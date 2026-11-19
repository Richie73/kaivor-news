"""Persistent local storage for the Kaivor News web app.

Keeps news configuration separate from the rendering/HTTP layer so future
milestones can move the storage backend without rewriting the UI.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
SOURCES_FILE = CONFIG_DIR / "news_sources.json"
SAVED_FILE = DATA_DIR / "news_saved.json"
RECEIPTS_FILE = DATA_DIR / "receipts.json"
RAMS_FILE = DATA_DIR / "rams.json"
READWISE_FILE = DATA_DIR / "readwise_highlights.json"
PRIVATE_SECRETS_FILE = Path.home() / ".config" / "kaivor" / "news_secrets.json"

_LOCK = RLock()


def _ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_dirs()
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def article_id(article: dict[str, Any]) -> str:
    """Return a stable ID based on URL first, then title/category."""
    link = str(article.get("link") or "").strip().lower()
    title = " ".join(str(article.get("title") or "").split()).lower()
    category = str(article.get("category") or "").strip().lower()
    seed = link if link and link != "#" else f"{category}|{title}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _clean_image_url(value: Any) -> str:
    """Sanitise an article image URL, or "" when it is not usable.

    Only http(s) URLs are kept: the URL is rendered in the browser as
    an <img src>, so javascript:/data: URIs and relative paths are
    rejected. This is the central choke point — every article passes
    through normalise_article on refresh and on save.

    FP075.1: the BBC's RSS feeds serve 240px-wide thumbnails
    (ichef.bbci.co.uk/.../standard/240/...), which look blurry
    stretched across a card — the BBC is the biggest image source
    in the feed (96 of 400 cards on 15 Nov 2026). The ichef
    service takes the width in the URL, so the width is bumped to
    1024 (verified live: the same image returns 1024x576). The
    Guardian's image URLs carry a signed hash, so they cannot be
    rewritten the same way — they stay at the 700px the API gives.
    FP075.2: the newer /images/ic/<WxH>/ form is rewritten too
    (240x135 -> 1024x576, verified live).
    """
    url = str(value or "").strip()
    if len(url) > 2048:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    if parsed.netloc == "ichef.bbci.co.uk":
        url = re.sub(
            r"(ichef\.bbci\.co\.uk/(?:ace/standard|news)/)\d+/",
            r"\g<1>1024/",
            url,
            count=1,
        )
        url = re.sub(
            r"(ichef\.bbci\.co\.uk/images/ic/)\d+x\d+/",
            r"\g<1>1024x576/",
            url,
            count=1,
        )
    return url


def _decode_entities(text: str) -> str:
    # Feeds sometimes carry HTML entities as literal text ("&nbsp;",
    # "&amp;"). The templates escape on render, so an undecoded entity
    # shows up literally on screen ("&nbsp;" in the middle of a
    # description, seen live 15 Nov 2026). Decode one level here; the
    # template re-escapes anything that needs it on the way out.
    return html.unescape(text).replace("\xa0", " ")


def _clean_description(value):
    # Some feeds carry the literal text "null"/"None" for a missing
    # summary (seen on ESPN live-blog entries, 15 Nov 2026). Treat
    # those as no description rather than showing the word.
    text = str(value or "").strip()
    if text.lower() in ("null", "none"):
        return ""
    return _decode_entities(text).strip()


def normalise_article(article: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": article_id(article),
        "title": _decode_entities(str(article.get("title") or "No Title")).strip(),
        "description": _clean_description(article.get("description")),
        "category": str(article.get("category") or "World").strip(),
        "source": str(article.get("source") or article.get("category") or "Unknown").strip(),
        "published": str(article.get("published") or "Recent").strip(),
        "published_ts": float(article.get("published_ts") or 0),
        "feed_tier": str(article.get("feed_tier") or "").strip(),
        "feed_url": str(article.get("feed_url") or "").strip(),
        "sport_focus": str(article.get("sport_focus") or "").strip(),
        "link": str(article.get("link") or "#").strip(),
        # FP126.1: Android intent URL for a puzzle's own app;
        # empty for everything else. Kept separate from "link"
        # because the feed quality gate rejects non-http(s) links.
        "app_link": str(article.get("app_link") or "").strip(),
        "image_url": _clean_image_url(article.get("image_url")),
        "image_illustrative": bool(article.get("image_illustrative", False)),
        "image_credit": str(article.get("image_credit") or "").strip(),
        "cluster_id": str(article.get("cluster_id") or "").strip(),
        "source_count": int(article.get("source_count") or 1),
        "report_count": int(article.get("report_count") or max(1, int(article.get("related_count") or 0) + 1)),
        "related_count": int(article.get("related_count") or 0),
        "confidence": str(article.get("confidence") or "Uncorroborated").strip(),
        "evidence_status": str(article.get("evidence_status") or article.get("confidence") or "Single-source").strip(),
        "developing": bool(article.get("developing", False)),
        "what_we_know_hint": str(article.get("what_we_know_hint") or "").strip(),
        "why_matters_hint": str(article.get("why_matters_hint") or article.get("impact_hint") or "").strip(),
        "impact_hint": str(article.get("impact_hint") or article.get("why_matters_hint") or "").strip(),
        "uncertainty_hint": str(article.get("uncertainty_hint") or "").strip(),
    }
    return item


# FP109: Richie does not want American-football or baseball stories in the
# feed (16 Nov 2026). Matching is whole-word/phrase on the title +
# description, plus the league URL paths (ESPN/BBC/Guardian/Sky all carry
# them even when the headline does not name the league). Deliberately NOT
# matched: "home run" and "pitcher" (common outside baseball).
# Basketball/NBA is NOT excluded.
# FP109.1: "touchdown" was first left out (spacecraft landings use it too),
# but a college-football story slipped through live with "touchdown" as
# its only signal word, so it is now matched. Accepted cost: a rare
# space-landing story using "touchdown" is dropped too.
# Known trade-off: "world series" also drops the occasional World Series of
# Darts/Poker story; the MLB World Series is baseball's biggest event, so
# the term stays.
_US_SPORT_PATTERNS = (
    re.compile(r"\bnfl\b", re.IGNORECASE),
    re.compile(r"\bsuper bowl\b", re.IGNORECASE),
    re.compile(r"\bamerican football\b", re.IGNORECASE),
    re.compile(r"\bcollege football\b", re.IGNORECASE),
    re.compile(r"\btouchdowns?\b", re.IGNORECASE),
    re.compile(r"\bquarterbacks?\b", re.IGNORECASE),
    re.compile(r"\bgridiron\b", re.IGNORECASE),
    re.compile(r"\bmlb\b", re.IGNORECASE),
    re.compile(r"\bworld series\b", re.IGNORECASE),
    re.compile(r"\bbaseballs?\b", re.IGNORECASE),
)
_US_SPORT_URL_PATHS = ("/nfl/", "/mlb/", "/american-football/", "/baseball/")


def is_us_sport_story(article: dict[str, Any]) -> bool:
    """Return True for American-football or baseball stories (FP109)."""
    text = f"{article.get('title') or ''} {article.get('description') or ''}"
    if any(pattern.search(text) for pattern in _US_SPORT_PATTERNS):
        return True
    try:
        path = urlparse(str(article.get("link") or "")).path.lower()
    except ValueError:
        return False
    return any(segment in path for segment in _US_SPORT_URL_PATHS)


def deduplicate_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove exact duplicate stories while preserving first-seen order.

    FP109: American-football and baseball stories are dropped here too —
    every refreshed article (RSS, Guardian, NewsData) passes through this
    function, so one filter covers all sources. Saved articles are not
    affected (they load through load_saved_articles, not this function).
    """
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for raw in articles:
        item = normalise_article(raw)
        if is_us_sport_story(item):
            continue
        key = item["id"]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def load_custom_sources() -> dict[str, list[str]]:
    with _LOCK:
        value = _read_json(SOURCES_FILE, {})
        if not isinstance(value, dict):
            return {}
        result: dict[str, list[str]] = {}
        for category, urls in value.items():
            if not isinstance(category, str) or not isinstance(urls, list):
                continue
            clean_urls = [str(url).strip() for url in urls if str(url).strip()]
            if clean_urls:
                result[category.strip()] = list(dict.fromkeys(clean_urls))
        return result


def save_custom_sources(sources: dict[str, list[str]]) -> None:
    clean: dict[str, list[str]] = {}
    for category, urls in sources.items():
        urls = [str(url).strip() for url in urls if str(url).strip()]
        if urls:
            clean[str(category).strip()] = list(dict.fromkeys(urls))
    with _LOCK:
        _write_json(SOURCES_FILE, clean)


def load_saved_articles() -> list[dict[str, Any]]:
    with _LOCK:
        value = _read_json(SAVED_FILE, [])
        if not isinstance(value, list):
            return []
        return [normalise_article(item) for item in value if isinstance(item, dict)]


def save_article(article: dict[str, Any]) -> dict[str, Any]:
    item = normalise_article(article)
    with _LOCK:
        current = load_saved_articles()
        current = [existing for existing in current if existing["id"] != item["id"]]
        current.insert(0, item)
        _write_json(SAVED_FILE, current[:500])
    return item


def remove_saved_article(article_id_value: str) -> bool:
    with _LOCK:
        current = load_saved_articles()
        filtered = [item for item in current if item["id"] != article_id_value]
        changed = len(filtered) != len(current)
        if changed:
            _write_json(SAVED_FILE, filtered)
        return changed


def is_saved(article_id_value: str) -> bool:
    return any(item["id"] == article_id_value for item in load_saved_articles())


# FP102: scanned receipts — same file-store pattern as saved articles.
def load_receipts() -> list[dict[str, Any]]:
    with _LOCK:
        value = _read_json(RECEIPTS_FILE, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]


def _receipt_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 2)
    return None


def save_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": "rcpt-" + uuid.uuid4().hex[:12],
        "merchant": receipt.get("merchant") if isinstance(receipt.get("merchant"), str) else None,
        "date": receipt.get("date") if isinstance(receipt.get("date"), str) else None,
        "total": _receipt_number(receipt.get("total")),
        "vat": _receipt_number(receipt.get("vat")),
        "currency": receipt.get("currency") if isinstance(receipt.get("currency"), str) else "GBP",
        "added": datetime.now(timezone.utc).isoformat(),
    }
    with _LOCK:
        current = load_receipts()
        current.insert(0, item)
        _write_json(RECEIPTS_FILE, current[:500])
    return item


def remove_receipt(receipt_id: str) -> bool:
    with _LOCK:
        current = load_receipts()
        filtered = [item for item in current if item.get("id") != receipt_id]
        changed = len(filtered) != len(current)
        if changed:
            _write_json(RECEIPTS_FILE, filtered)
        return changed


# FP105: Readwise highlights — one payload dict, replaced whole on sync.
def load_readwise_highlights() -> dict[str, Any]:
    with _LOCK:
        value = _read_json(READWISE_FILE, {})
        if not isinstance(value, dict):
            return {"highlights": [], "last_sync": 0, "total": 0, "complete": True}
        highlights = value.get("highlights")
        return {
            "highlights": [item for item in highlights if isinstance(item, dict)]
            if isinstance(highlights, list)
            else [],
            "last_sync": value.get("last_sync") or 0,
            "total": value.get("total") or 0,
            "complete": value.get("complete", True) is not False,
        }


def save_readwise_highlights(payload: dict[str, Any]) -> dict[str, Any]:
    stored = {
        "highlights": [item for item in payload.get("highlights", []) if isinstance(item, dict)],
        "last_sync": payload.get("last_sync") or 0,
        "total": payload.get("total") or 0,
        "complete": payload.get("complete", True) is not False,
    }
    with _LOCK:
        _write_json(READWISE_FILE, stored)
    return stored


# FP100: RAMS drafts — same file-store pattern as saved articles.
def load_rams_list() -> list[dict[str, Any]]:
    with _LOCK:
        value = _read_json(RAMS_FILE, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]


def _rams_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _rams_lines(value: Any, cap: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:cap]


def _rams_rating(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, number))


def _normalise_rams(rams: dict[str, Any]) -> dict[str, Any]:
    risks = []
    for row in rams.get("risks") or []:
        if not isinstance(row, dict) or not _rams_text(row.get("hazard")):
            continue
        risks.append({
            "hazard": _rams_text(row.get("hazard")),
            "who": _rams_text(row.get("who")) or "Operatives",
            "severity": _rams_rating(row.get("severity")),
            "likelihood": _rams_rating(row.get("likelihood")),
            "residual_severity": _rams_rating(row.get("residual_severity")),
            "residual_likelihood": _rams_rating(row.get("residual_likelihood")),
            "controls": _rams_lines(row.get("controls"), 8),
        })
    return {
        "task": _rams_text(rams.get("task")),
        "site": _rams_text(rams.get("site")),
        "date": _rams_text(rams.get("date")),
        "prepared_by": _rams_text(rams.get("prepared_by")) or "Richard Gallagher",
        "company": _rams_text(rams.get("company")) or "Gallagher Construction Services",
        "plant": _rams_text(rams.get("plant")),
        "method_steps": _rams_lines(rams.get("method_steps"), 30),
        "risks": risks[:20],
        "ppe": _rams_lines(rams.get("ppe"), 12),
    }


def save_rams(rams: dict[str, Any]) -> dict[str, Any]:
    item = _normalise_rams(rams)
    item["id"] = "rams-" + uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    item["created"] = now
    item["updated"] = now
    with _LOCK:
        current = load_rams_list()
        current.insert(0, item)
        _write_json(RAMS_FILE, current[:200])
    return item


def get_rams(rams_id: str) -> dict[str, Any] | None:
    for item in load_rams_list():
        if item.get("id") == rams_id:
            return item
    return None


def update_rams(rams_id: str, rams: dict[str, Any]) -> dict[str, Any] | None:
    item = _normalise_rams(rams)
    with _LOCK:
        current = load_rams_list()
        for index, existing in enumerate(current):
            if existing.get("id") != rams_id:
                continue
            item["id"] = rams_id
            item["created"] = existing.get("created") or existing.get("updated") or datetime.now(timezone.utc).isoformat()
            item["updated"] = datetime.now(timezone.utc).isoformat()
            current[index] = item
            _write_json(RAMS_FILE, current)
            return item
    return None


def remove_rams(rams_id: str) -> bool:
    with _LOCK:
        current = load_rams_list()
        filtered = [item for item in current if item.get("id") != rams_id]
        changed = len(filtered) != len(current)
        if changed:
            _write_json(RAMS_FILE, filtered)
        return changed


def _secret_aliases() -> dict[str, str]:
    return {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "guardian": "GUARDIAN_API_KEY",
        "brave": "BRAVE_API_KEY",
        "newsdata": "NEWSDATA_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }


def _read_secret_dict(path: Path) -> dict[str, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return {str(k): str(v).strip() for k, v in value.items()
                if isinstance(value, dict) and str(v).strip()} if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def load_secrets() -> dict[str, str]:
    """Load provider credentials from environment variables and private storage.

    Project-local credential files are never read.
    """
    with _LOCK:
        private = _read_secret_dict(PRIVATE_SECRETS_FILE)
        result: dict[str, str] = {}
        for key, env_name in _secret_aliases().items():
            result[key] = os.environ.get(env_name, "").strip() or private.get(key, "")
        return result


def save_secret(secret_type: str, api_key: str) -> bool:
    """Persist a provider key in the private user store, never the project tree."""
    aliases = set(_secret_aliases())
    secret_type = str(secret_type).strip().lower()
    api_key = str(api_key).strip()
    if secret_type not in aliases or not api_key:
        return False
    with _LOCK:
        path = PRIVATE_SECRETS_FILE
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                path.parent.chmod(0o700)
            except OSError:
                pass
            current = _read_secret_dict(path)
            current[secret_type] = api_key
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(current, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, path)
                try:
                    path.chmod(0o600)
                except OSError:
                    pass
            finally:
                try:
                    os.unlink(tmp_name)
                except FileNotFoundError:
                    pass
            return True
        except OSError:
            return False

