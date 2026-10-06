"""Story evolution and timeline engine for Kaivor News FP015.

This module is deliberately deterministic. It does not decide whether a report is
true and it does not invent missing events. It orders the reports Kaivor currently
has for a story and describes the observable progression of coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any
from urllib.parse import urlparse


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_published(value: Any) -> datetime | None:
    """Parse common RSS/ISO publication timestamps into timezone-aware UTC."""
    text = _clean(value)
    if not text:
        return None

    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text[:-1] + "+00:00")

    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass

    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def _token_set(article: dict[str, Any]) -> set[str]:
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    return set(re.findall(r"[a-z0-9]{4,}", text))


def _overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    a = _token_set(left)
    b = _token_set(right)
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _coverage_type(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return "First report"
    if current.get("source") == previous.get("source"):
        return "Repeat coverage"
    if _overlap(current, previous) >= 0.55:
        return "Follow-up coverage"
    return "Additional report"


def _status(report_count: int, first_dt: datetime | None, latest_dt: datetime | None) -> str:
    if report_count <= 1:
        return "New"
    if not first_dt or not latest_dt:
        return "Developing"
    age_hours = max(0.0, (latest_dt - first_dt).total_seconds() / 3600.0)
    if age_hours >= 24:
        return "Evolving"
    return "Developing"


def build_story_timeline(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Return an ordered, conservative timeline for one story cluster."""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in members:
        item_id = _clean(item.get("id"))
        if item_id and item_id in seen:
            continue
        if item_id:
            seen.add(item_id)
        unique.append(dict(item))

    dated = []
    undated = []
    for item in unique:
        dt = parse_published(item.get("published"))
        if dt is None:
            undated.append(item)
        else:
            dated.append((dt, item))

    dated.sort(key=lambda pair: pair[0])
    ordered = [item for _, item in dated] + undated

    events: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for index, item in enumerate(ordered):
        dt = parse_published(item.get("published"))
        events.append(
            {
                "id": _clean(item.get("id")),
                "title": _clean(item.get("title")) or "Untitled report",
                "source": _clean(item.get("source")) or "Unknown source",
                "published": _clean(item.get("published")) or "Publication time unavailable",
                "published_iso": dt.isoformat() if dt else None,
                "link": _clean(item.get("link")) or "#",
                "coverage_type": _coverage_type(item, previous),
                "is_first": index == 0,
                "is_latest": index == len(ordered) - 1,
            }
        )
        previous = item

    first_dt = dated[0][0] if dated else None
    latest_dt = dated[-1][0] if dated else None
    report_count = len(ordered)

    if report_count:
        latest = ordered[-1]
        latest_source = _clean(latest.get("source")) or "Unknown source"
        latest_title = _clean(latest.get("title")) or "Untitled report"
        if report_count == 1:
            change_summary = "Kaivor currently has one report for this story."
        else:
            change_summary = (
                f"Kaivor currently has {report_count} reports for this story. "
                f"The latest report is from {latest_source}: {latest_title}"
            )
    else:
        change_summary = "Kaivor currently has no reports for this story."

    return {
        "report_count": report_count,
        "timeline": events,
        "story_status": _status(report_count, first_dt, latest_dt),
        "first_published": first_dt.isoformat() if first_dt else None,
        "latest_published": latest_dt.isoformat() if latest_dt else None,
        "latest_source": _clean(ordered[-1].get("source")) if ordered else "",
        "change_summary": change_summary,
        "based_on_current_reports": True,
    }
