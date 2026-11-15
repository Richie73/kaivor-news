"""FP089: stock photo fallback — Openverse images for imageless articles.

Server: stock_images.py derives keywords from the headline, fetches
one Openverse image (no API key), and caches per query. The
/api/stock_image route exposes it. A miss or failure is
success:false, never a 500.

Template: imageless cards render a placeholder div with the
headline; an IntersectionObserver fetches the photo when the card
scrolls into view and swaps it in with an "Illustrative photo"
caption + credit. Saving a card carries the flag and credit through
articleFromCard and normalise_article, so the Saved view shows the
same marking.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

import main
import stock_images
from news_store import normalise_article

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

OPENVERSE_PAYLOAD = {
    "result_count": 1,
    "results": [{
        "url": "https://images.example.com/stadium.jpg",
        "title": "A football stadium",
        "creator": "Jane Doe",
        "license": "by",
        "license_version": "2.0",
        "foreign_landing_url": "https://example.com/stadium",
    }],
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_stock_cache():
    stock_images._cache.clear()
    yield
    stock_images._cache.clear()


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


# --- keywords -------------------------------------------------------

def test_keywords_from_headline():
    assert stock_images.keywords_from_headline(
        "The new football stadium opens after long delays"
    ) == ["new", "football", "stadium", "opens", "long", "delays"]
    assert stock_images.keywords_from_headline(
        "Chelsea beat Manchester City in the cup final"
    ) == ["Chelsea", "beat", "Manchester", "City", "cup", "final"]
    # "new" stays: dropping it would break New Zealand / New York.
    assert stock_images.keywords_from_headline(
        "Wales fans ecstatic after win over New Zealand"
    ) == ["Wales", "fans", "ecstatic", "win", "New", "Zealand"]


def test_keywords_empty_headline():
    assert stock_images.keywords_from_headline("") == []
    assert stock_images.keywords_from_headline("The a an of to") == []
    assert stock_images.get_stock_image("The a an of to") is None


# --- candidate queries (FP089.1) ------------------------------------

def test_candidate_queries_wales_headline():
    words = stock_images.keywords_from_headline(
        "'We've waited 73 years to be here' - Wales fans ecstatic "
        "after win over New Zealand"
    )
    assert stock_images._candidate_queries(words) == [
        "We've waited years here Wales",
        "Wales New Zealand",
        "Zealand",
    ]


def test_candidate_queries_no_proper_nouns():
    words = stock_images.keywords_from_headline(
        "rain expected across the country tomorrow"
    )
    assert stock_images._candidate_queries(words) == [
        "rain expected across country tomorrow",
        "expected",
    ]


def test_candidate_queries_single_word():
    assert stock_images._candidate_queries(["Rain"]) == ["Rain"]
    assert stock_images._candidate_queries([]) == []


def test_get_stock_image_falls_back_to_shorter_query():
    calls = []

    def fake_fetch(query):
        calls.append(query)
        if query == "We've waited years here Wales":
            return None
        return {"url": "https://images.example.com/wales.jpg",
                "credit": "Jane · CC0", "query": query}

    with patch.object(stock_images, "_fetch_from_openverse",
                      side_effect=fake_fetch):
        result = stock_images.get_stock_image(
            "'We've waited 73 years to be here' - Wales fans ecstatic "
            "after win over New Zealand"
        )
    assert result["url"] == "https://images.example.com/wales.jpg"
    assert result["query"] == "Wales New Zealand"
    assert calls == ["We've waited years here Wales", "Wales New Zealand"]
    # Second call for the same headline costs no new lookup.
    with patch.object(stock_images, "_fetch_from_openverse",
                      side_effect=fake_fetch):
        assert stock_images.get_stock_image(
            "'We've waited 73 years to be here' - Wales fans ecstatic "
            "after win over New Zealand"
        )["url"] == "https://images.example.com/wales.jpg"
    assert len(calls) == 2


def test_get_stock_image_all_fail_then_cached():
    with patch.object(stock_images, "_fetch_from_openverse",
                      return_value=None) as fetch:
        assert stock_images.get_stock_image(
            "Zxqwv jklmnop qrstuv wxyzab cdefgh"
        ) is None
        # Full query + the lone capitalised word; the single-word
        # fallback is the same word, so it is not tried twice.
        assert fetch.call_count == 2
        assert stock_images.get_stock_image(
            "Zxqwv jklmnop qrstuv wxyzab cdefgh"
        ) is None
        assert fetch.call_count == 2


# --- fetch + cache --------------------------------------------------

def test_fetch_returns_first_result_with_credit():
    with patch.object(stock_images.requests, "get",
                      return_value=FakeResponse(200, OPENVERSE_PAYLOAD)) as get:
        result = stock_images.get_stock_image("football stadium opens")
    assert result == {"url": "https://images.example.com/stadium.jpg",
                      "credit": "Jane Doe · CC BY 2.0",
                      "query": "football stadium opens"}
    assert get.call_count == 1
    _, kwargs = get.call_args
    assert kwargs["params"]["license_type"] == "commercial"
    assert kwargs["params"]["page_size"] == 1


def test_fetch_no_results_returns_none():
    with patch.object(stock_images.requests, "get",
                      return_value=FakeResponse(200, {"results": []})):
        assert stock_images.get_stock_image("football stadium") is None


def test_fetch_http_error_returns_none():
    with patch.object(stock_images.requests, "get",
                      return_value=FakeResponse(500, {})):
        assert stock_images.get_stock_image("football stadium") is None


def test_fetch_exception_returns_none():
    with patch.object(stock_images.requests, "get",
                      side_effect=RuntimeError("boom")):
        assert stock_images.get_stock_image("football stadium") is None


def test_cache_hit_skips_second_fetch():
    with patch.object(stock_images.requests, "get",
                      return_value=FakeResponse(200, OPENVERSE_PAYLOAD)) as get:
        first = stock_images.get_stock_image("football stadium opens")
        second = stock_images.get_stock_image("Football stadium opens!")
    assert first == second
    assert get.call_count == 1


def test_failure_is_retried_after_ttl():
    with patch.object(stock_images.requests, "get",
                      return_value=FakeResponse(200, {"results": []})) as get:
        assert stock_images.get_stock_image("football stadium") is None
        assert stock_images.get_stock_image("football stadium") is None
        # FP089.1: the first call tries both candidates ("football
        # stadium", then "football"); the repeat call is cached.
        assert get.call_count == 2
    with patch.object(stock_images.time, "time",
                      return_value=stock_images.time.time() + 61):
        with patch.object(stock_images.requests, "get",
                          return_value=FakeResponse(200, OPENVERSE_PAYLOAD)) as get:
            assert stock_images.get_stock_image("football stadium") is not None
            assert get.call_count == 1


def test_cache_evicts_oldest(monkeypatch):
    monkeypatch.setattr(stock_images, "_STOCK_CACHE_MAX_ENTRIES", 2)
    stock_images._cache_put("one", {"url": "a"})
    stock_images._cache_put("two", {"url": "b"})
    stock_images._cache_put("three", {"url": "c"})
    assert "one" not in stock_images._cache
    assert "two" in stock_images._cache
    assert "three" in stock_images._cache


def test_credit_for_variants():
    assert stock_images._credit_for(
        {"creator": "", "license": "cc0", "license_version": ""}) == "CC0"
    assert stock_images._credit_for(
        {"creator": "Jane", "license": "", "license_version": ""}) == "Jane"
    assert stock_images._credit_for(
        {"creator": "", "license": "", "license_version": ""}) == ""


# --- route ----------------------------------------------------------

def test_route_returns_image():
    with patch.object(main, "get_stock_image",
                      return_value={"url": "https://images.example.com/x.jpg",
                                    "credit": "Jane · CC0",
                                    "query": "football stadium"}):
        res = main.app.test_client().get(
            "/api/stock_image", query_string={"q": "football stadium"})
    assert res.status_code == 200
    assert res.get_json() == {"success": True,
                              "image_url": "https://images.example.com/x.jpg",
                              "credit": "Jane · CC0",
                              "query": "football stadium"}


def test_route_missing_headline_is_400():
    res = main.app.test_client().get("/api/stock_image")
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_route_no_result_is_success_false():
    with patch.object(main, "get_stock_image", return_value=None):
        res = main.app.test_client().get(
            "/api/stock_image", query_string={"q": "football stadium"})
    assert res.status_code == 200
    assert res.get_json() == {"success": False}


# --- normalise_article ----------------------------------------------

def test_normalise_keeps_illustrative_fields():
    item = normalise_article({
        "title": "T", "link": "https://example.com/t",
        "image_url": "https://images.example.com/x.jpg",
        "image_illustrative": True, "image_credit": "Jane · CC0",
    })
    assert item["image_illustrative"] is True
    assert item["image_credit"] == "Jane · CC0"
    plain = normalise_article({"title": "T", "link": "https://example.com/t"})
    assert plain["image_illustrative"] is False
    assert plain["image_credit"] == ""


def test_normalise_drops_null_description():
    # FP089.1: some feeds carry the literal text "null"/"None" for a
    # missing summary (seen on ESPN live-blog entries, 15 Nov 2026).
    assert normalise_article(
        {"title": "T", "description": "null"})["description"] == ""
    assert normalise_article(
        {"title": "T", "description": "None"})["description"] == ""
    assert normalise_article(
        {"title": "T", "description": "Real summary"})["description"] == (
        "Real summary")


# --- template --------------------------------------------------------

def test_placeholder_in_jinja_card():
    html = template_text()
    assert '{% else %}<div class="card-image card-image-placeholder skeleton" data-stock-headline="{{ article.title }}"></div>{% endif %}' in html
    assert ".card-image-placeholder { cursor:default; }" in html
    assert ".stock-credit { font-size:10px; color:var(--faint); margin:-4px 0 8px; }" in html


def test_observer_and_loader():
    html = template_text()
    assert "const stockPhotoObserver = ('IntersectionObserver' in window) ? new IntersectionObserver" in html
    assert "function observeStockPlaceholders(root = document) {" in html
    assert "async function loadStockPhoto(placeholder) {" in html
    assert "const res = await fetch('/api/stock_image?q=' + encodeURIComponent(headline), {cache:'no-store'});" in html
    assert "caption.textContent = 'Illustrative photo' + (data.credit ? ' · ' + data.credit : '');" in html
    assert "card.dataset.imageIllustrative = '1';" in html
    assert "if (data.credit) card.dataset.imageCredit = data.credit;" in html


def test_saved_render_carries_illustrative_marking():
    html = template_text()
    assert "<div class=\"stock-credit\">Illustrative photo${article.image_credit ? ' · ' + escapeHtml(article.image_credit) : ''}</div>" in html
    assert '<div class="card-image card-image-placeholder skeleton" data-stock-headline="${escapeAttr(article.title)}"></div>' in html


def test_article_from_card_reads_illustrative_flags():
    html = template_text()
    assert "image_illustrative: card.dataset.imageIllustrative === '1'," in html
    assert "image_credit: card.dataset.imageCredit || ''," in html


def test_observe_called_after_renders():
    html = template_text()
    assert html.count("observeStockPlaceholders();") == 1
    assert "observeStockPlaceholders(container);" in html
