"""Persistent local storage for the Kaivor News web app.

Keeps news configuration separate from the rendering/HTTP layer so future
milestones can move the storage backend without rewriting the UI.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
SOURCES_FILE = CONFIG_DIR / "news_sources.json"
SAVED_FILE = DATA_DIR / "news_saved.json"
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
    """
    url = str(value or "").strip()
    if len(url) > 2048:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url


def normalise_article(article: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": article_id(article),
        "title": str(article.get("title") or "No Title").strip(),
        "description": str(article.get("description") or "").strip(),
        "category": str(article.get("category") or "World").strip(),
        "source": str(article.get("source") or article.get("category") or "Unknown").strip(),
        "published": str(article.get("published") or "Recent").strip(),
        "published_ts": float(article.get("published_ts") or 0),
        "feed_tier": str(article.get("feed_tier") or "").strip(),
        "feed_url": str(article.get("feed_url") or "").strip(),
        "sport_focus": str(article.get("sport_focus") or "").strip(),
        "link": str(article.get("link") or "#").strip(),
        "image_url": _clean_image_url(article.get("image_url")),
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


def deduplicate_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove exact duplicate stories while preserving first-seen order."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for raw in articles:
        item = normalise_article(raw)
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

