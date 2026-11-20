"""FP128: puzzle cards get no stock photos.

20 Nov 2026: the Wordle card ("The New York Times - Wordle Daily
Challenge") showed a water-park photo of kids on inflatable toys,
credited Eva Rinaldi. The fallback's single-word query for that
title is "Challenge" (the longest distinctive word), Openverse
returns challenge-tagged photos, and "Puzzles" is ungated so one
keyword hit passes. Puzzle cards are links to puzzle apps, not
stories — a guessed photo can only misfire, so both layers stop:
the template renders no stock placeholder for Puzzles cards, and
the endpoint refuses the category outright.
"""
from pathlib import Path
from unittest.mock import patch

import main
import stock_images
from stock_images import (
    _candidate_queries,
    _distinctive_words,
    get_stock_image,
    keywords_from_headline,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
WORDLE_TITLE = "The New York Times - Wordle Daily Challenge"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_wordle_title_fallback_query_is_challenge():
    """Regression: documents WHY the misfire happened — the
    single-word fallback for the Wordle title is the generic word
    "Challenge", which matches unrelated challenge-tagged photos."""
    words = keywords_from_headline(WORDLE_TITLE)
    queries = _candidate_queries(_distinctive_words(words))
    assert queries[-1] == "Challenge"


def test_get_stock_image_returns_none_for_puzzles():
    def _no_fetch(*args, **kwargs):
        raise AssertionError("must not reach Openverse for Puzzles")

    with patch.object(stock_images.requests, "get", side_effect=_no_fetch):
        assert get_stock_image(WORDLE_TITLE, "Puzzles") is None


def test_get_stock_image_puzzles_case_insensitive():
    assert get_stock_image(WORDLE_TITLE, "puzzles") is None
    assert get_stock_image(WORDLE_TITLE, "PUZZLES") is None
    assert get_stock_image(WORDLE_TITLE, " Puzzles ") is None


def test_get_stock_image_still_serves_news():
    hit = {"url": "https://images.example.com/x.jpg",
           "credit": "Jane · CC0", "query": "football stadium"}
    with patch.object(stock_images, "_fetch_from_openverse",
                      return_value=hit):
        assert get_stock_image("Lions win at home", "Sport") == hit


def test_stock_image_route_refuses_puzzles():
    res = main.app.test_client().get(
        "/api/stock_image",
        query_string={"q": WORDLE_TITLE, "category": "Puzzles"})
    assert res.status_code == 200
    assert res.get_json() == {"success": False}


def test_jinja_card_skips_placeholder_for_puzzles():
    html = template_text()
    assert "{% elif article.category != 'Puzzles' %}" in html
    assert "{% else %}<div class=\"card-image card-image-placeholder" not in html


def test_js_card_skips_placeholder_for_puzzles():
    html = template_text()
    assert "article.category === 'Puzzles' ? ''" in html
    # The placeholder still exists for every other card.
    assert '<div class="card-image card-image-placeholder skeleton" data-stock-headline="${escapeAttr(article.title)}"></div>' in html
