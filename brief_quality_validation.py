"""Deterministic structural checks for generated Kaivor News briefs.

These checks identify common formatting and evidence-preservation problems.
Evidence attribution, uncertainty, and material figures must appear in WHAT IS REPORTED,
not merely in analysis or follow-up sections. These checks do not establish truth.
"""
from __future__ import annotations

import re
from typing import Any

REQUIRED_SECTIONS = (
    "WHAT IS REPORTED",
    "WHY IT MATTERS",
    "WHAT TO WATCH NEXT",
)

# Check financial amounts and percentages, not incidental dates or counts.
MATERIAL_NUMBER_RE = re.compile(
    r"(?<!\w)(?:£|\$|€)\s?\d[\d,]*(?:\.\d+)?"
    r"(?:\s?(?:million|billion|thousand))?"
    r"|(?<!\w)\d[\d,]*(?:\.\d+)?\s?%",
    re.IGNORECASE,
)


def _normalise_number(value: str) -> str:
    return re.sub(r"[\s,]", "", value).lower()


def _reported_section(text: str) -> str:
    """Extract WHAT IS REPORTED so evidence checks cannot be satisfied by later sections."""
    heading = re.compile(
        r"(?im)^\s*(?:\d+\s*[).:-]\s*)?(?:\*\*)?WHAT IS REPORTED(?:\*\*)?\s*:?[ \t]*"
    )
    start = heading.search(text)
    if not start:
        return ""
    remainder = text[start.end():]
    next_heading = re.search(
        r"(?im)^\s*(?:\d+\s*[).:-]\s*)?(?:\*\*)?(?:WHY IT MATTERS|WHAT TO WATCH NEXT)(?:\*\*)?\s*:?[ \t]*",
        remainder,
    )
    return remainder[:next_heading.start()] if next_heading else remainder


def validate_brief(
    brief: Any,
    article: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return structural validation results for an AI or fallback brief."""
    text = str(brief or "").strip()
    article = article if isinstance(article, dict) else {}
    upper = text.upper()
    lower = text.lower()
    reported = _reported_section(text)
    reported_lower = reported.lower()
    issues: list[str] = []

    missing_sections = [
        section for section in REQUIRED_SECTIONS if section not in upper
    ]
    if missing_sections:
        issues.append("missing_sections")

    if len(text) < 100:
        issues.append("brief_too_short")

    source_type = str(article.get("source_type") or "article").strip().lower()
    source = str(article.get("source") or "").strip()

    if source_type == "pasted_text":
        if not any(
            phrase in reported_lower
            for phrase in (
                "user-supplied",
                "pasted text",
                "supplied text",
                "source is not supplied",
            )
        ):
            issues.append("missing_pasted_text_attribution")
    elif source and source.lower() not in reported_lower:
        issues.append("missing_source_attribution")

    confidence = str(article.get("confidence_label") or "").strip().lower()
    status = str(article.get("evidence_status") or "").strip().lower()
    try:
        source_count = int(article.get("source_count", 1))
    except (TypeError, ValueError):
        source_count = 1

    low_confidence = (
        source_count < 2
        or confidence in {"low", "very low", "uncorroborated"}
        or "single-source" in status
    )
    uncertainty_phrases = (
        "not independently corroborated",
        "has not been independently corroborated",
        "has not been independently verified",
        "not independently verified",
        "not been independently verified",
        "unverified",
        "uncorroborated",
        "provisional",
        "low confidence",
        "single-source",
        "does not independently verify",
    )
    if low_confidence and not any(
        phrase in reported_lower for phrase in uncertainty_phrases
    ):
        issues.append("missing_uncertainty")

    source_material = " ".join(
        str(article.get(key) or "") for key in ("title", "description")
    )
    material_numbers = MATERIAL_NUMBER_RE.findall(source_material)
    normalised_brief = _normalise_number(reported_lower)
    missing_numbers = [
        number.strip()
        for number in material_numbers
        if _normalise_number(number) not in normalised_brief
    ]
    if missing_numbers:
        issues.append("source_figures_not_preserved")

    return {
        "valid": not issues,
        "issues": issues,
        "missing_sections": missing_sections,
        "checked_numeric_tokens": len(material_numbers),
        "missing_numeric_tokens": missing_numbers,
    }
