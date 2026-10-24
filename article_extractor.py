"""Conservative, quality-aware article text retrieval for Kaivor News.

The extractor never runs page scripts. It validates public HTTP(S) destinations,
revalidates every redirect, limits response size/time, prefers semantic article
containers, filters common page chrome, and rejects low-quality boilerplate.
This is best-effort extraction, not publisher verification.
"""
from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
TIMEOUT = (3.05, 7)
USER_AGENT = "KaivorNews/FP028 (+article text retrieval; no browser execution)"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "aside", "form", "button", "select", "option", "iframe", "template"}
BLOCK_TAGS = {"p", "article", "main", "section", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "blockquote", "pre"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
ARTICLE_MARKERS = ("article-body", "story-body", "article-content", "story-content", "entry-content", "post-content", "article__body", "story__body", "content-body", "article-text", "articlebody")
BOILERPLATE_MARKERS = (
    "cookie", "consent", "paywall", "subscribe", "subscription", "newsletter",
    "recommendation", "related-stories", "related-articles", "social-share", "share-tools",
    "breadcrumb", "navigation", "navbar", "sidebar", "advert", "sponsored-content",
    "sign-in", "signin", "login", "register", "modal", "popup", "overlay", "toolbar",
    "comments", "footer", "header-nav", "site-header", "site-menu", "promo-banner",
)
BOILERPLATE_PHRASES = (
    "accept cookies", "cookie preferences", "manage cookies", "privacy policy", "terms of use",
    "all rights reserved", "sign in to continue", "subscribe now", "already a subscriber",
    "create a free account", "enable javascript", "skip to content", "related articles",
    "you may also like", "read more stories", "follow us on", "share this article",
    "advertisement", "your browser does not support", "newsletter sign up",
)


def _normalise_lines(parts: list[str]) -> list[str]:
    raw = "".join(parts).replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
    return [line for line in lines if line]


def _clean_parts(parts: list[str]) -> str:
    lines = _normalise_lines(parts)
    kept = []
    for line in lines:
        low = line.casefold()
        # Remove short, recognisable boilerplate lines; do not drop long story
        # paragraphs just because they mention cookies, subscriptions, or sharing.
        if len(line) <= 220 and any(phrase in low for phrase in BOILERPLATE_PHRASES):
            continue
        if len(line) <= 100 and low in {"home", "menu", "search", "sign in", "log in", "subscribe", "advertisement", "comments"}:
            continue
        kept.append(line)
    # Deduplicate adjacent repeated snippets often emitted by responsive layouts.
    deduped = []
    for line in kept:
        if not deduped or line.casefold() != deduped[-1].casefold():
            deduped.append(line)
    return " ".join(deduped)[:30000].strip()


def _quality_score(text: str) -> int:
    """Return a conservative 0-100 heuristic score, not a truth/confidence score."""
    if not text:
        return 0
    words = re.findall(r"[\w’'-]+", text.casefold())
    if not words:
        return 0
    chars = len(text)
    sentence_count = len(re.findall(r"[.!?](?:[\"’')\]]*)?(?:\s|$)", text))
    unique_ratio = len(set(words)) / max(1, len(words))
    score = min(30, int(chars / 50))
    score += min(20, sentence_count * 3)
    score += min(20, max(0, len(words) // 35) * 2)
    score += min(20, int(unique_ratio * 25))
    low = text.casefold()
    boilerplate_hits = sum(1 for phrase in BOILERPLATE_PHRASES if phrase in low)
    score -= min(45, boilerplate_hits * 12)
    return max(0, min(100, score))


class _TextExtractor(HTMLParser):
    """Collect whole-page text and candidate article/main content separately."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[dict] = []
        self.active_candidates: list[dict] = []
        self.candidates: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        marker = " ".join(str(attrs.get(k) or "") for k in ("id", "class", "role", "itemprop", "data-testid")).casefold()
        inherited_skip = bool(self.stack and self.stack[-1]["skip"])
        marker_skip = any(term in marker for term in BOILERPLATE_MARKERS)
        skip = inherited_skip or tag in SKIP_TAGS or marker_skip
        candidate = None
        if not skip and (tag in {"article", "main"} or any(term in marker for term in ARTICLE_MARKERS) or attrs.get("itemprop") == "articleBody"):
            candidate = {"tag": tag, "marker": marker, "parts": []}
            self.candidates.append(candidate)
            self.active_candidates.append(candidate)
        frame = {"tag": tag, "skip": skip, "candidate": candidate}
        if tag not in VOID_TAGS:
            self.stack.append(frame)
        if not skip and tag in BLOCK_TAGS:
            self.parts.append("\n")
            for active in self.active_candidates:
                active["parts"].append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i]["tag"] == tag), None)
        if idx is None:
            return
        removed = self.stack[idx:]
        del self.stack[idx:]
        for frame in reversed(removed):
            candidate = frame["candidate"]
            if candidate is not None and candidate in self.active_candidates:
                # Remove by identity, not dict equality (candidate dictionaries
                # may have identical content before their children are parsed).
                self.active_candidates = [item for item in self.active_candidates if item is not candidate]
        if not (self.stack and self.stack[-1]["skip"]) and tag in BLOCK_TAGS:
            self.parts.append("\n")
            for active in self.active_candidates:
                active["parts"].append("\n")

    def handle_data(self, data):
        if not data.strip() or (self.stack and self.stack[-1]["skip"]):
            return
        clean = " ".join(data.split())
        self.parts.append(clean + " ")
        for candidate in self.active_candidates:
            candidate["parts"].append(clean + " ")


def _extract_html(html: str) -> dict[str, str | int] | None:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML is common; still assess the text collected so far.
        pass

    options = []
    for candidate in parser.candidates:
        text = _clean_parts(candidate["parts"])
        if len(text) >= 400:
            options.append((text, _quality_score(text), "semantic_container"))

    # Prefer a semantic article/main container, but assess all candidates rather
    # than accepting the first long container (which may be recommendations).
    if options:
        text, score, source = max(options, key=lambda item: (item[1], len(item[0])))
        if score >= 38:
            return {"text": text, "quality_score": score, "content_source": source}

    # Some publishers use no semantic article markup. A whole-page fallback is
    # allowed only when it looks like substantial prose, not merely long chrome.
    whole_text = _clean_parts(parser.parts)
    score = _quality_score(whole_text)
    if len(whole_text) >= 400 and score >= 60:
        return {"text": whole_text, "quality_score": score, "content_source": "page_text_fallback"}
    return None


def _validate_public_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False, "unsupported_scheme"
        if not parsed.hostname or parsed.username or parsed.password:
            return False, "invalid_url"
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            addresses = [ip]
        except ValueError:
            try:
                addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
            except (OSError, ValueError):
                return False, "dns_failed"
        if not addresses or any(not address.is_global for address in addresses):
            return False, "private_host"
        return True, ""
    except Exception:
        return False, "invalid_url"


def extract_article_text(url: str) -> dict[str, str | bool | int]:
    """Fetch an article from a public URL and return it only if text quality passes."""
    current = str(url or "").strip()
    if len(current) > 2048:
        return {"success": False, "status": "invalid_url", "message": "The article URL is too long."}
    for hop in range(MAX_REDIRECTS + 1):
        allowed, reason = _validate_public_url(current)
        if not allowed:
            return {"success": False, "status": reason, "message": "The article URL is not publicly accessible or could not be validated."}
        try:
            response = requests.get(
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=False,
            )
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location or hop >= MAX_REDIRECTS:
                        return {"success": False, "status": "redirect_limit", "message": "The publisher redirected too many times."}
                    current = urljoin(current, location)
                    continue
                if response.status_code != 200:
                    return {"success": False, "status": "http_error", "message": f"The publisher returned HTTP {response.status_code}."}
                content_type = response.headers.get("Content-Type", "").lower()
                if "html" not in content_type and "xhtml" not in content_type:
                    return {"success": False, "status": "not_html", "message": "The publisher did not return an HTML article page."}
                chunks = []
                size = 0
                for chunk in response.iter_content(chunk_size=16384):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_BYTES:
                        return {"success": False, "status": "too_large", "message": "The article page exceeded the retrieval size limit."}
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                html = b"".join(chunks).decode(encoding, errors="replace")
                extracted = _extract_html(html)
                if not extracted:
                    return {"success": False, "status": "extraction_failed", "message": "Readable, article-like text could not be extracted with sufficient quality."}
                return {
                    "success": True,
                    "status": "full_text",
                    "text": extracted["text"],
                    "quality_score": extracted["quality_score"],
                    "content_source": extracted["content_source"],
                    "final_url": current,
                }
            finally:
                response.close()
        except requests.RequestException:
            return {"success": False, "status": "network_error", "message": "The publisher could not be reached."}
    return {"success": False, "status": "redirect_limit", "message": "The publisher redirected too many times."}
