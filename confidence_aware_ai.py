"""Build conservative, source-attributed prompts and fallbacks for AI briefs."""
from __future__ import annotations

from typing import Any


def _text(article: dict[str, Any], key: str, default: str = "") -> str:
    value = article.get(key, default)
    return str(value if value is not None else default).strip()


def _positive_int(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def confidence_context(article: dict[str, Any]) -> dict[str, Any]:
    """Normalise article evidence metadata without inferring verification."""
    source_type = _text(article, "source_type", "article").lower()
    is_pasted_text = source_type == "pasted_text"
    source = ("User-supplied text" if is_pasted_text else (_text(article, "source", "Unknown source") or "Unknown source"))
    source_count = _positive_int(article.get("source_count"), 1)
    report_count = _positive_int(article.get("report_count"), 1)
    confidence_label = _text(article, "confidence_label", "Low") or "Low"
    evidence_status = _text(article, "evidence_status", "Single-source") or "Single-source"
    sources = article.get("story_sources")
    if isinstance(sources, (list, tuple)):
        source_names = [str(item).strip() for item in sources if str(item).strip()]
    else:
        source_names = []
    if not source_names and not is_pasted_text:
        source_names = [source]

    low_confidence = is_pasted_text or (
        source_count < 2
        or confidence_label.lower() in {"low", "very low", "uncorroborated"}
        or "single-source" in evidence_status.lower()
    )
    return {
        "source_type": source_type,
        "is_pasted_text": is_pasted_text,
        "source": source,
        "source_count": source_count,
        "report_count": report_count,
        "confidence_label": confidence_label,
        "evidence_status": evidence_status,
        "sources": source_names,
        "low_confidence": low_confidence,
    }


def build_ai_brief_messages(article: dict[str, Any]) -> list[dict[str, str]]:
    """Create a source-aware AI prompt; never upgrade the supplied evidence."""
    evidence = confidence_context(article)
    title = _text(article, "title", "Untitled report") or "Untitled report"
    description = _text(article, "description", "No article summary supplied.") or "No article summary supplied."
    published = _text(article, "published", "Not supplied") or "Not supplied"
    category = _text(article, "category", "News") or "News"
    if evidence["is_pasted_text"]:
        uncertainty = (
            "USER-SUPPLIED TEXT: The following content was pasted by the user, not retrieved from the selected news card. "
            "Do not attribute it to the card's publisher or any named outlet unless the pasted text itself explicitly identifies that source. "
            "The origin and accuracy of the pasted content are unverified; state that limitation clearly and do not imply independent corroboration."
        )
    elif evidence["low_confidence"]:
        uncertainty = (
            "LOW CONFIDENCE WARNING: This is single-source or otherwise low-confidence reporting. Attribute the event to the named publisher (for example, 'SOURCE reports that…'); explicitly say it has not been independently corroborated by the supplied context. Do not present the central claim as an established fact."
        )
    else:
        uncertainty = "The supplied metadata indicates more than one source group, but this alone does not prove every detail. Attribute specific claims and do not claim independent confirmation beyond the supplied evidence status."
    system = (
        "You are Kaivor News' cautious news analyst. Use only the article details and evidence metadata supplied by the user. "
        "Produce exactly three labelled sections: WHAT IS REPORTED, WHY IT MATTERS, and WHAT TO WATCH NEXT. "
        "In WHAT IS REPORTED, name and attribute the report to its publisher. Preserve uncertainty and distinguish reported claims from verified facts. "
        "Do not invent facts, motives, figures, causal links, sanctions, dates, outcomes, or details absent from the supplied text. "
        "If information is missing, say so plainly. The next-outlook section must describe possibilities, not predict them as facts. "
        + uncertainty
    )
    user = (
        f"Article title: {title}\nArticle summary: {description}\nCategory: {category}\nPublished: {published}\n"
        f"Source type: {evidence['source_type']}\n"
        f"Primary publisher: {'Not supplied (user-pasted content)' if evidence['is_pasted_text'] else evidence['source']}\n"
        f"Available source groups: {', '.join(evidence['sources']) if evidence['sources'] else 'None supplied'}\n"
        f"Independent source-group count supplied by Kaivor: {'Not available for pasted text' if evidence['is_pasted_text'] else evidence['source_count']}\n"
        f"Related report count: {evidence['report_count']}\nConfidence label: {evidence['confidence_label']}\n"
        f"Evidence status: {evidence['evidence_status']}\n\n"
        "Generate the three-section brief while preserving the evidence limits above."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_ai_brief_fallback(article: dict[str, Any]) -> str:
    """Return a safe, useful fallback when an AI provider is unavailable."""
    evidence = confidence_context(article)
    title = _text(article, "title", "Untitled report") or "Untitled report"
    description = _text(article, "description", "No article summary supplied.") or "No article summary supplied."
    if evidence["is_pasted_text"]:
        status = (
            f"The supplied text describes: {title}. Its original publisher and accuracy cannot be verified "
            "from the pasted text alone; the content has not been independently corroborated in the available Kaivor context."
        )
    elif evidence["low_confidence"]:
        status = (
            f"{evidence['source']} reports: {title}. The supplied feed marks this as "
            f"{evidence['evidence_status'].lower()} with {evidence['confidence_label'].lower()} confidence; "
            "the claim has not been independently corroborated in the available Kaivor context."
        )
    else:
        status = (
            f"Kaivor has grouped {evidence['report_count']} related report(s) from "
            f"{evidence['source_count']} independent source group(s). Current evidence status: "
            f"{evidence['evidence_status']}. This does not independently verify every detail."
        )
    summary = f"Article context supplied: {description}" if description else "The feed supplies no article summary."
    return (
        f"1) WHAT IS REPORTED: {status}\n\n"
        f"2) WHY IT MATTERS: The potential significance depends on the details confirmed by the source and any independent evidence.\n\n"
        f"3) WHAT TO WATCH NEXT: Look for primary evidence, a named official statement, or independent reporting that confirms or corrects the account.\n\n"
        f"Source context: {summary}"
    )
