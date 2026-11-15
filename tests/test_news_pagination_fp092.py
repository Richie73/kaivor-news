"""FP092: faster news list — 50 stories at a time plus
content-visibility on cards.

The page renders every story into the DOM (600+ on a full feed).
Only the first 50 show; "Load more stories" reveals the next 50,
and the button hides itself when every matching story is shown.
Cards also get content-visibility so the browser skips painting
off-screen ones. Matching is computed from the current category,
not from display state (loadMoreNews does not reset display, so
reading display would count only the cards already visible).
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_ASSERTIONS = """
assert.deepEqual(newsVisibleSlice(646, 50), {shown: 50, remaining: 596});
assert.deepEqual(newsVisibleSlice(646, 100), {shown: 100, remaining: 546});
assert.deepEqual(newsVisibleSlice(30, 50), {shown: 30, remaining: 0});
assert.deepEqual(newsVisibleSlice(0, 50), {shown: 0, remaining: 0});
assert.deepEqual(newsVisibleSlice(50, 50), {shown: 50, remaining: 0});
"""


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, start, end):
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), html, re.S)
    assert match, f"could not slice {start!r}..{end!r}"
    return match.group(1)


def test_page_size_is_fifty():
    assert "const NEWS_PAGE_SIZE = 50;" in template_text()


def test_load_more_markup_present():
    html = template_text()
    assert 'id="news-load-more"' in html
    assert 'id="news-load-more-count"' in html
    assert 'id="news-load-more-btn"' in html
    assert 'onclick="loadMoreNews()"' in html
    assert "Load more stories" in html


def test_filter_category_resets_page_and_applies_pagination():
    html = template_text()
    body = function_body(
        html,
        "function filterCategory(category, element) {",
        "// FP092 NEWS PAGINATION: BEGIN",
    )
    assert "newsCurrentCategory = category;" in body
    assert "newsVisibleCount = NEWS_PAGE_SIZE;" in body
    assert "applyNewsPagination();" in body


def test_apply_pagination_counts_from_category_not_display():
    html = template_text()
    body = function_body(
        html,
        "function applyNewsPagination() {",
        "function loadMoreNews() {",
    )
    assert "newsVisibleSlice(matching.length, newsVisibleCount)" in body
    assert "skeleton-card" in body
    assert "newsCurrentCategory" in body
    assert "Showing ' + state.shown + ' of ' + matching.length + ' stories'" in body


def test_views_hide_the_load_more_button():
    html = template_text()
    cache = function_body(
        html,
        "function cacheNewsContainer() {",
        "// FP088 SKELETONS:",
    )
    assert "hideNewsLoadMore();" in cache
    weather = function_body(
        html,
        "function showWeather(element) {",
        "function hideWeatherView() {",
    )
    assert "hideNewsLoadMore();" in weather
    markets = function_body(
        html,
        "function showMarkets() {",
        "function hideMarketsView() {",
    )
    assert "hideNewsLoadMore();" in markets


def test_pagination_applies_on_page_load():
    html = template_text()
    assert "applyNewsPagination();" in html
    load = function_body(
        html,
        "document.addEventListener('DOMContentLoaded',()=>{",
        "});\n</script>",
    )
    assert "applyNewsPagination();" in load


def test_card_content_visibility_css():
    html = template_text()
    assert ".card { content-visibility:auto; contain-intrinsic-size:0 340px; }" in html


def test_pagination_slice_logic_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    match = re.search(
        r"function newsVisibleSlice\(total, visibleCount\) \{(.*?)\n\}",
        html,
        re.S,
    )
    assert match, "newsVisibleSlice helper missing"
    js = match.group(0)
    script = "import assert from 'node:assert/strict';\n" + js + NODE_ASSERTIONS
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run(
        [node, path], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
