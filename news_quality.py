"""Conservative quality checks for supplemental news articles.

This module intentionally rejects only clear promotional/legal-solicitation
patterns. It does not judge an article by its category or country alone.
"""
import re


_LEGAL_MARKETING_PATTERNS = (
    r"\bshareholder alert\b",
    r"\bsecurities fraud\b",
    r"\bsecurities class action\b",
    r"\bclass action lawsuit\b",
    r"\binvestigation on behalf of investors\b",
    r"\binvestor deadline\b",
    r"\blead plaintiff deadline\b",
    r"\bcontact the (?:firm|law firm)\b",
    r"\binvestors are reminded\b",
)

_PROMOTIONAL_PATTERNS = (
    r"\btop stocks to buy now\b",
    r"\bstocks to buy now\b",
    r"\bbuy now before\b",
    r"\bguaranteed returns\b",
    r"\bguaranteed profits\b",
    r"\bpenny stock alert\b",
    r"\bunlock explosive growth\b",
)


def _article_text(article):
    """Build normalised searchable text from the available article fields."""
    fields = (
        article.get("title"),
        article.get("description"),
        article.get("content"),
        article.get("source"),
        article.get("source_name"),
    )
    return " ".join(str(value) for value in fields if value).lower()


def quality_rejection_reason(article):
    """Return a rejection reason for clear spam, otherwise an empty string."""
    if not isinstance(article, dict):
        return "invalid article"

    text = _article_text(article)

    has_legal_marketing_language = any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in _LEGAL_MARKETING_PATTERNS
    )
    has_legal_context = any(
        term in text
        for term in (
            "law firm",
            "attorneys",
            "class action",
            "securities",
            "shareholder",
            "investigation on behalf",
            "lead plaintiff",
        )
    )
    if has_legal_marketing_language and has_legal_context:
        return "investor legal solicitation"

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in _PROMOTIONAL_PATTERNS
    ):
        return "overt investment promotion"

    return ""


def is_low_quality_article(article):
    """True only when a clear low-quality promotional pattern is detected."""
    return bool(quality_rejection_reason(article))
