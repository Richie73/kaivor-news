"""Fresh, multi-source news collection for Kaivor News FP017.1.

Goals:
- broad but curated publisher coverage across every news category;
- parallel RSS retrieval so one slow source does not block the whole refresh;
- timestamp-aware filtering so old feed items do not reappear as "latest" news;
- deterministic newest-first ordering;
- enough reports per source for Kaivor's evidence/corroboration engine;
- custom RSS sources remain supported.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import os
import re
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests


DEFAULT_MAX_AGE_HOURS = max(1, int(os.environ.get("KAIVOR_NEWS_MAX_AGE_HOURS", "72")))
DEFAULT_ITEMS_PER_FEED = max(5, int(os.environ.get("KAIVOR_NEWS_ITEMS_PER_FEED", "15")))
MAX_WORKERS = max(4, int(os.environ.get("KAIVOR_NEWS_MAX_WORKERS", "12")))

# Curated defaults: several independent publishers per category without
# deliberately filling the feed with low-quality aggregators.
DEFAULT_FEEDS: dict[str, list[dict[str, str]]] = {
    "World": [
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "tier": "primary"},
        {"name": "CNN", "url": "http://rss.cnn.com/rss/edition_world.rss", "tier": "major"},
        {"name": "NPR", "url": "https://feeds.npr.org/1001/rss.xml", "tier": "major"},
    ],
    "Technology": [
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/uk/technology/rss", "tier": "primary"},
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "tier": "specialist"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "tier": "specialist"},
        {"name": "Wired", "url": "https://www.wired.com/feed/rss", "tier": "specialist"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "tier": "specialist"},
    ],
    "Business": [
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/uk/business/rss", "tier": "primary"},
        {"name": "CNBC", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "tier": "major"},
        {"name": "NPR", "url": "https://feeds.npr.org/1006/rss.xml", "tier": "major"},
    ],
    "Science": [
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/science/rss", "tier": "primary"},
        {"name": "ScienceDaily", "url": "https://www.sciencedaily.com/rss/top/science.xml", "tier": "specialist"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/science", "tier": "specialist"},
    ],
    "UK": [
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/uk/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/uk/rss", "tier": "primary"},
        {"name": "Sky News", "url": "https://feeds.skynews.com/feeds/rss/uk.xml", "tier": "major"},
    ],
    "Sport": [
        # Football-specific feeds are deliberately included ahead of general
        # sports feeds so the Sport section can be football-first without
        # excluding other major sports.
        {"name": "BBC Sport Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "tier": "primary", "sport_focus": "football"},
        {"name": "The Guardian Football", "url": "https://www.theguardian.com/football/rss", "tier": "primary", "sport_focus": "football"},
        {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "tier": "primary"},
        {"name": "The Guardian", "url": "https://www.theguardian.com/uk/sport/rss", "tier": "primary"},
        {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "tier": "major"},
        {"name": "Sky Sports", "url": "https://feeds.skynews.com/feeds/rss/sports.xml", "tier": "major"},
    ],
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_html(raw_html: str) -> str:
    text = re.sub(r"<.*?>", " ", raw_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 160:
        text = text[:157] + "..."
    return text


def parse_published(value: Any) -> datetime | None:
    """Parse common RSS/Atom publication formats into UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = _clean(value)
        if not text:
            return None
        dt = None
        for candidate in (text, text[:-1] + "+00:00" if text.endswith("Z") else text):
            try:
                dt = datetime.fromisoformat(candidate)
                break
            except ValueError:
                pass
        if dt is None:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError, OverflowError):
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def entry_datetime(entry: Any) -> datetime | None:
    """Prefer structured RSS timestamps, then textual published/updated values."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass
    for key in ("published", "updated", "pubDate", "date"):
        dt = parse_published(entry.get(key))
        if dt:
            return dt
    return None


def iso_datetime(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_name_from_url(url: str, fallback: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host.split(".")[0].title() or fallback
    except Exception:
        return fallback


def build_feed_registry(custom_sources: dict[str, list[str]] | None = None) -> dict[str, list[dict[str, str]]]:
    """Return curated defaults plus user-configured feeds, without duplicates."""
    registry = {category: [dict(feed) for feed in feeds] for category, feeds in DEFAULT_FEEDS.items()}
    for category, urls in (custom_sources or {}).items():
        registry.setdefault(category, [])
        known = {feed["url"] for feed in registry[category]}
        for url in urls:
            clean_url = _clean(url)
            if clean_url and clean_url not in known:
                registry[category].append({
                    "name": source_name_from_url(clean_url, category),
                    "url": clean_url,
                    "tier": "custom",
                })
                known.add(clean_url)
    return registry


def _fetch_feed(feed: dict[str, str], category: str, now: datetime, max_age_hours: int, items_per_feed: int) -> list[dict[str, Any]]:
    url = feed["url"]
    try:
        parsed = feedparser.parse(url, request_headers={"User-Agent": "Kaivor-News/FP017.1"})
    except Exception:
        return []
    if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
        return []

    feed_title = _clean(parsed.feed.get("title")) or feed.get("name") or source_name_from_url(url, category)
    items: list[dict[str, Any]] = []
    for entry in list(parsed.entries):
        published_dt = entry_datetime(entry)
        if published_dt:
            age_hours = (now - published_dt).total_seconds() / 3600
            if age_hours < -6:
                # Ignore obviously broken future-dated feed items.
                continue
            if age_hours > max_age_hours:
                continue
        elif not entry.get("title"):
            continue

        raw_desc = entry.get("summary", entry.get("description", ""))
        title = _clean(entry.get("title") or "No Title")
        link = _clean(entry.get("link") or "#")
        combined_text = f"{title} {clean_html(raw_desc)}".lower()
        football_terms = (
            "football", "soccer", "premier league", "champions league",
            "europa league", "conference league", "fa cup", "efl",
            "fifa", "uefa", "wsl", "women's super league", "ballon d'or",
            "goalkeeper", "striker", "midfielder", "transfer window",
            "footballer", "offside", "penalty shootout",
        )
        is_football = bool(feed.get("sport_focus") == "football" or any(term in combined_text for term in football_terms))

        items.append({
            "title": title,
            "description": clean_html(raw_desc),
            "category": category,
            "source": _clean(feed.get("name")) or feed_title,
            "published": iso_datetime(published_dt) or "Recent",
            "published_ts": published_dt.timestamp() if published_dt else 0,
            "link": link,
            "feed_tier": feed.get("tier", "custom"),
            "feed_url": url,
            "sport_focus": "football" if is_football else "other",
        })
    items.sort(key=lambda item: float(item.get("published_ts") or 0), reverse=True)
    return items[:items_per_feed]


def fetch_multi_source_news(custom_sources: dict[str, list[str]] | None = None, *, now: datetime | None = None, max_age_hours: int = DEFAULT_MAX_AGE_HOURS, items_per_feed: int = DEFAULT_ITEMS_PER_FEED) -> list[dict[str, Any]]:
    """Fetch all configured feeds in parallel and return newest items first."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    registry = build_feed_registry(custom_sources)
    jobs: list[tuple[str, dict[str, str]]] = []
    for category, feeds in registry.items():
        for feed in feeds:
            jobs.append((category, feed))

    articles: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(jobs)))) as executor:
        futures = [executor.submit(_fetch_feed, feed, category, now, max_age_hours, items_per_feed) for category, feed in jobs]
        for future in as_completed(futures):
            try:
                articles.extend(future.result())
            except Exception:
                pass

    # Sport is intentionally football-first while retaining other sports.
    # Within each group, newest publication time still wins.
    articles.sort(
        key=lambda item: (
            1 if item.get("category") == "Sport" and item.get("sport_focus") == "football" else 0,
            float(item.get("published_ts") or 0),
        ),
        reverse=True,
    )
    return articles
