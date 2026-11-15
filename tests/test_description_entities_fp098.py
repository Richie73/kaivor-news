"""FP098: feed text carrying HTML entities as literal text.

Some feeds send "&nbsp;" (and friends) as literal characters in
the description. The templates escape on render, so the "&"
became "&amp;" and the card showed "&nbsp;" on screen — seen live
on the Anthropic IPO card, 15 Nov 2026. normalise_article now
decodes entities once (titles and descriptions); the template
re-escapes anything that needs it on the way out.
"""
from news_store import normalise_article


def test_nbsp_in_description_becomes_a_space():
    item = normalise_article(
        {"title": "T", "description": "putting&nbsp;AI investors first"}
    )
    assert item["description"] == "putting AI investors first"


def test_ampersand_entity_decodes():
    item = normalise_article(
        {"title": "T", "description": "Fish &amp; Chips shop reopens"}
    )
    assert item["description"] == "Fish & Chips shop reopens"


def test_title_entities_decode():
    item = normalise_article({"title": "Marks &amp; Spencer", "description": ""})
    assert item["title"] == "Marks & Spencer"


def test_null_description_still_empty():
    item = normalise_article({"title": "T", "description": "null"})
    assert item["description"] == ""


def test_plain_description_unchanged():
    item = normalise_article({"title": "T", "description": "Plain text here."})
    assert item["description"] == "Plain text here."
