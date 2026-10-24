"""Conservative article text retrieval for Kaivor News.

Security controls:
- Only HTTP(S) URLs on public hosts are allowed.
- DNS results are checked for private, loopback, link-local, reserved and
  non-global addresses.
- Redirects are followed manually and each destination is revalidated.
- Response size and time are bounded; no scripts are executed.
This is best-effort extraction, not publisher verification.
"""
from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
TIMEOUT = (3.05, 7)
USER_AGENT = "KaivorNews/FP026 (+article text retrieval; no browser execution)"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "button"}
BLOCK_TAGS = {"p", "article", "main", "section", "div", "br", "li", "h1", "h2", "h3", "h4", "blockquote"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.article_depth = 0
        self.article_score = 0
        self.best_text = []
        self.best_score = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            self.stack.append(("skip", tag))
            return
        if self.skip_depth:
            self.stack.append(("nested", tag))
            return
        marker = " ".join(str(attrs.get(k) or "") for k in ("id", "class", "role")).lower()
        if tag in {"article", "main"} or any(word in marker for word in ("article-body", "story-body", "article-content", "story-content", "entry-content", "post-content")):
            self.article_depth += 1
            self.stack.append(("article", tag))
        else:
            self.stack.append(("normal", tag))
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self.stack:
            return
        # HTML can be imperfect; unwind to matching open tag.
        idx = next((i for i in range(len(self.stack)-1, -1, -1) if self.stack[i][1] == tag), None)
        if idx is None:
            return
        removed = self.stack[idx:]
        del self.stack[idx:]
        for kind, _ in reversed(removed):
            if kind == "skip":
                self.skip_depth = max(0, self.skip_depth - 1)
            elif kind == "article":
                self.article_depth = max(0, self.article_depth - 1)
        if not self.skip_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth and data.strip():
            clean = " ".join(data.split())
            self.parts.append(clean + " ")
            if self.article_depth:
                self.article_score += len(clean)

    def text(self):
        text = " ".join(" ".join(self.parts).split())
        return text[:30000]


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


def _extract_html(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    text = parser.text()
    # Reject generic pages and pages that contain too little useful text.
    return text if len(text) >= 400 else ""


def extract_article_text(url: str) -> dict[str, str | bool]:
    """Fetch and extract readable text from a public article URL."""
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
                    return {"success": False, "status": "extraction_failed", "message": "Readable article text could not be extracted; the publisher may use a paywall or dynamic page."}
                return {"success": True, "status": "full_text", "text": extracted, "final_url": current}
            finally:
                response.close()
        except requests.RequestException:
            return {"success": False, "status": "network_error", "message": "The publisher could not be reached."}
    return {"success": False, "status": "redirect_limit", "message": "The publisher redirected too many times."}
