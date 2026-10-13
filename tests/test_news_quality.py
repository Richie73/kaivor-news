"""Regression tests for conservative supplemental-news quality filtering."""
from news_quality import is_low_quality_article, quality_rejection_reason


def article(title, description="", category="Business", source="Example News"):
    return {
        "title": title,
        "description": description,
        "category": category,
        "source": source,
        "link": "https://example.com/story",
    }


def test_rejects_investor_law_firm_solicitation():
    item = article(
        "Shareholder Alert: Investors Reminded of Deadline",
        "A law firm announces an investigation on behalf of investors "
        "over alleged securities fraud.",
    )
    assert is_low_quality_article(item)
    assert quality_rejection_reason(item) == "investor legal solicitation"


def test_rejects_overt_stock_promotion():
    item = article(
        "Penny Stock Alert: Buy Now Before It Rises",
        "Promotional market commentary.",
    )
    assert is_low_quality_article(item)


def test_keeps_legitimate_business_reporting():
    item = article(
        "UK manufacturer reports record annual revenue",
        "The company said revenue rose 12% as demand improved.",
    )
    assert not is_low_quality_article(item)


def test_keeps_major_corporate_news():
    item = article(
        "Company announces new battery factory in Wales",
        "The project is expected to create 800 jobs.",
    )
    assert not is_low_quality_article(item)


def test_keeps_football_reporting():
    item = article(
        "Premier League club confirms new manager",
        "The appointment follows the club's review of recent results.",
        category="Sport",
        source="Football News",
    )
    assert not is_low_quality_article(item)


def test_handles_missing_fields_safely():
    assert not is_low_quality_article({"title": "Flood warnings issued"})
    assert not is_low_quality_article({})
    assert is_low_quality_article(None)
