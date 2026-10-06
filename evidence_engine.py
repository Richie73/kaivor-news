"""Evidence and corroboration engine for Kaivor News FP013.

The engine separates three things that are easy to confuse:
1. reports: individual articles/items;
2. source groups: independent publishers/outlets;
3. corroboration: agreement across independent source groups.

It is deterministic and conservative. It never treats repeated coverage from the
same publisher as independent confirmation.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

SOURCE_ALIASES = {
    "bbc": "BBC News",
    "bbc news": "BBC News",
    "reuters": "Reuters",
    "cnn": "CNN",
    "cnn international": "CNN",
    "the guardian": "The Guardian",
    "guardian": "The Guardian",
    "the independent": "The Independent",
    "independent": "The Independent",
    "sky news": "Sky News",
    "sky": "Sky News",
    "associated press": "Associated Press",
    "ap": "Associated Press",
    "npr": "NPR",
    "al jazeera": "Al Jazeera",
    "financial times": "Financial Times",
    "the times": "The Times",
    "the telegraph": "The Telegraph",
    "techcrunch": "TechCrunch",
    "the verge": "The Verge",
    "espn": "ESPN",
}

DOMAIN_ALIASES = {
    "bbc.co.uk": "BBC News",
    "bbc.com": "BBC News",
    "reuters.com": "Reuters",
    "cnn.com": "CNN",
    "theguardian.com": "The Guardian",
    "independent.co.uk": "The Independent",
    "sky.com": "Sky News",
    "apnews.com": "Associated Press",
    "npr.org": "NPR",
    "aljazeera.com": "Al Jazeera",
    "ft.com": "Financial Times",
    "thetimes.co.uk": "The Times",
    "telegraph.co.uk": "The Telegraph",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "espn.com": "ESPN",
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonical_source(article: dict[str, Any]) -> str:
    """Return a stable publisher identity for an article."""
    source = _clean(article.get("source"))
    source_key = source.lower().strip(" .,-")
    if source_key in SOURCE_ALIASES:
        return SOURCE_ALIASES[source_key]

    link = _clean(article.get("link"))
    if link:
        try:
            host = (urlparse(link).hostname or "").lower()
            host = host[4:] if host.startswith("www.") else host
            for domain, canonical in DOMAIN_ALIASES.items():
                if host == domain or host.endswith("." + domain):
                    return canonical
            if host:
                return host
        except ValueError:
            pass

    return source or "Unknown source"


def source_key(article: dict[str, Any]) -> str:
    return canonical_source(article).lower()


def build_evidence_model(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Build conservative evidence metadata for one story cluster."""
    reports = []
    seen_report_ids: set[str] = set()
    for item in members:
        report_id = _clean(item.get("id"))
        if report_id and report_id in seen_report_ids:
            continue
        if report_id:
            seen_report_ids.add(report_id)
        reports.append(item)

    source_names: dict[str, str] = {}
    for item in reports:
        key = source_key(item)
        source_names.setdefault(key, canonical_source(item))

    source_count = len(source_names)
    report_count = len(reports)
    source_reports = Counter(source_key(item) for item in reports)
    repeated_same_source = sum(max(0, count - 1) for count in source_reports.values())

    if source_count >= 3:
        evidence_status = "Corroborated — 3+ independent sources"
        confidence = "Higher confidence"
    elif source_count == 2:
        evidence_status = "Corroborated — 2 independent sources"
        confidence = "Corroborated"
    elif report_count > 1:
        evidence_status = "Single-source — multiple reports"
        confidence = "Related coverage"
    else:
        evidence_status = "Single-source"
        confidence = "Uncorroborated"

    return {
        "story_sources": sorted(source_names.values()),
        "source_keys": sorted(source_names),
        "source_count": source_count,
        "report_count": report_count,
        "related_count": max(0, report_count - 1),
        "repeated_same_source_reports": repeated_same_source,
        "evidence_status": evidence_status,
        "confidence": confidence,
        "corroborated": source_count >= 2,
        "independent_source_count": source_count,
        "source_report_counts": dict(sorted(source_reports.items())),
    }


def evidence_sentence(model: dict[str, Any]) -> str:
    """Return a user-facing explanation of the current evidence state."""
    sources = int(model.get("source_count", 1) or 1)
    reports = int(model.get("report_count", 1) or 1)
    repeated = int(model.get("repeated_same_source_reports", 0) or 0)
    names = [str(name) for name in model.get("story_sources", []) if str(name).strip()]
    source_text = ", ".join(names)

    if sources >= 2:
        sentence = f"Kaivor has {reports} related reports from {sources} independent source groups."
        if source_text:
            sentence += f" Sources: {source_text}."
    elif reports > 1:
        sentence = f"Kaivor has {reports} related reports from the same source group; these are not independent corroboration."
        if source_text:
            sentence += f" Source: {source_text}."
    else:
        sentence = "Kaivor currently has one report from one source group."
        if source_text:
            sentence += f" Source: {source_text}."

    if repeated:
        sentence += f" {repeated} additional report{'s' if repeated != 1 else ''} repeat the same source group."
    return sentence
