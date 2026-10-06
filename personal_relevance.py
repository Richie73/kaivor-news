"""Deterministic personal relevance engine for Kaivor News FP017.

Personal relevance is deliberately separate from global story importance and
confidence. It answers: "How relevant is this story to the user's configured
interests?" It does not claim the story is important or true.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from threading import RLock
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
PROFILE_FILE = CONFIG_DIR / "news_relevance_profile.json"
_LOCK = RLock()

DEFAULT_PROFILE: dict[str, Any] = {
    "categories": {
        "Technology": 5,
        "Business": 4,
        "Science": 4,
        "UK": 4,
        "World": 3,
        "Sport": 2,
    },
    "keywords": ["AI", "artificial intelligence", "construction", "finance", "business", "technology"],
    "regions": ["UK", "United Kingdom"],
}

CATEGORY_BASE = {
    "technology": 30,
    "business": 28,
    "science": 26,
    "uk": 28,
    "world": 20,
    "sport": 15,
    "puzzles": 8,
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalise_keywords(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        item = _clean(value)
        if item and item.lower() not in {x.lower() for x in result}:
            result.append(item[:80])
    return result[:40]


def _normalise_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        profile = {}
    raw_categories = profile.get("categories") if isinstance(profile.get("categories"), dict) else {}
    categories: dict[str, int] = {}
    for key, value in raw_categories.items():
        name = _clean(key)
        if not name:
            continue
        try:
            weight = max(0, min(5, int(value)))
        except (TypeError, ValueError):
            continue
        categories[name] = weight
    if not categories:
        categories = dict(DEFAULT_PROFILE["categories"])

    regions = _normalise_keywords(profile.get("regions"))
    if not regions:
        regions = list(DEFAULT_PROFILE["regions"])

    keywords = _normalise_keywords(profile.get("keywords"))
    if not keywords:
        keywords = list(DEFAULT_PROFILE["keywords"])

    return {"categories": categories, "keywords": keywords, "regions": regions}


def load_profile() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        try:
            data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
            return _normalise_profile(data)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            profile = _normalise_profile(DEFAULT_PROFILE)
            save_profile(profile)
            return profile


def save_profile(profile: dict[str, Any]) -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    normalised = _normalise_profile(profile)
    temp = PROFILE_FILE.with_suffix(".tmp")
    with _LOCK:
        temp.write_text(json.dumps(normalised, indent=2), encoding="utf-8")
        temp.replace(PROFILE_FILE)
    return normalised


def _text(article: dict[str, Any]) -> str:
    return _clean(f"{article.get('title', '')} {article.get('description', '')}").lower()


def calculate_personal_relevance(article: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = _normalise_profile(profile if profile is not None else load_profile())
    category = _clean(article.get("category"))
    category_key = category.lower()
    text = _text(article)

    base = CATEGORY_BASE.get(category_key, 12)
    reasons: list[str] = []
    category_weight = 0
    for name, weight in profile["categories"].items():
        if name.lower() == category_key:
            category_weight = weight
            break
    category_bonus = category_weight * 7
    if category_bonus:
        reasons.append(f"Category preference: {category} (+{category_bonus}).")

    matched_keywords: list[str] = []
    for keyword in profile["keywords"]:
        if keyword.lower() in text:
            matched_keywords.append(keyword)
    keyword_bonus = min(28, len(matched_keywords) * 7)
    if matched_keywords:
        reasons.append(f"Interest match: {', '.join(matched_keywords[:4])} (+{keyword_bonus}).")

    region_bonus = 0
    matched_regions: list[str] = []
    for region in profile["regions"]:
        if region.lower() in text:
            matched_regions.append(region)
    if matched_regions:
        region_bonus = 12
        reasons.append(f"Region match: {', '.join(matched_regions[:3])} (+{region_bonus}).")
    elif category_key == "uk" and any(r.lower() in {"uk", "united kingdom"} for r in profile["regions"]):
        region_bonus = 8
        reasons.append(f"UK category relevance (+{region_bonus}).")

    score = min(100, max(0, base + category_bonus + keyword_bonus + region_bonus))
    label = "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    if not reasons:
        reasons.append("No strong match with the configured personal-interest profile.")
    reasons.append("Personal relevance is based on the configured profile; it is separate from story importance and evidence confidence.")

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
        "matched_keywords": matched_keywords,
        "matched_regions": matched_regions,
        "category": category,
    }


def enrich_personal_relevance(articles: list[dict[str, Any]], profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    profile = _normalise_profile(profile if profile is not None else load_profile())
    enriched: list[dict[str, Any]] = []
    for article in articles:
        item = dict(article)
        assessment = calculate_personal_relevance(item, profile)
        item["relevance_score"] = assessment["score"]
        item["relevance_label"] = assessment["label"]
        item["relevance_reasons"] = assessment["reasons"]
        item["relevance_keywords"] = assessment["matched_keywords"]
        item["relevance_regions"] = assessment["matched_regions"]
        enriched.append(item)
    return enriched
