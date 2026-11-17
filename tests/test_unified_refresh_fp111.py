"""FP111: one refresh button in the title row, following the view.

Three refresh buttons used to overlap: the news button showed in
every view (even Chat), the market panel had its own "Refresh
markets" button, and the Markets view had a third "Refresh" button
— so the Markets view showed all three at once. Now a single
button refreshes the news in the news views, the markets in the
Markets view (prices plus the five-day history, as before), and
hides in Weather, the Hub and the container views (Saved, Chat,
Settings, Receipts, RAMS, Memories). Settings stays in the header.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, opener, next_opener):
    start = html.index(opener)
    end = html.index(next_opener, start)
    return html[start:end]


def test_single_refresh_button_markup():
    html = template_text()
    row = re.search(
        r'<div id="section-title-row">(.*?)</div>', html, re.S)
    assert row, "section-title-row missing"
    assert 'id="refresh-btn"' in row.group(1)
    assert 'onclick="refreshCurrentView(this)"' in row.group(1)
    assert "↻ Refresh news" in row.group(1)


def test_old_refresh_buttons_are_gone():
    html = template_text()
    assert "refresh-news-btn" not in html
    assert "market-refresh" not in html
    assert 'onclick="refreshMarketsFromView()"' not in html
    assert ">↻ Refresh</button>" not in html


def test_settings_stays_in_the_header():
    html = template_text()
    header = re.search(r"<header>(.*?)</header>", html, re.S)
    assert header, "header missing"
    assert 'id="settings-btn"' in header.group(1)
    assert 'onclick="showSettings(this)"' in header.group(1)


def test_update_refresh_button_call_sites():
    html = template_text()
    for opener, closer in [
        ("function filterCategory(category, element) {",
         "// FP092 NEWS PAGINATION: BEGIN"),
        ("function showWeather(element) {", "function hideWeatherView() {"),
        ("function showMarkets() {", "function hideMarketsView() {"),
        ("function showMorningHub(element) {",
         "function hideMorningHubView() {"),
        ("function restoreNewsContainer() {",
         "// FP111 UNIFIED REFRESH: BEGIN"),
    ]:
        body = function_body(html, opener, closer)
        assert "updateRefreshButton();" in body, opener
    cache = function_body(
        html,
        "function cacheNewsContainer() {",
        "// FP088 SKELETONS:",
    )
    # After the early return: the FP099 test pins the exact two
    # opening lines, and the button must still hide when a view
    # opens (the return only fires when a view is already open).
    assert cache.index("if (newsViewReplaced) return;") < cache.index(
        "updateRefreshButton();")


def test_refresh_functions_restore_via_update():
    html = template_text()
    news = re.search(
        r"async function refreshNewsFromButton\(button\) \{(.*?)\n\}",
        html, re.S)
    assert news, "refreshNewsFromButton missing"
    assert "updateRefreshButton();" in news.group(1)
    assert "button.textContent = '↻ Refresh news'" not in news.group(1)
    markets = re.search(
        r"async function refreshMarkets\(\) \{(.*?)\n\}", html, re.S)
    assert markets, "refreshMarkets missing"
    assert "getElementById('refresh-btn')" in markets.group(1)
    assert "updateRefreshButton();" in markets.group(1)
    assert "button.textContent = '↻ Refresh markets'" not in markets.group(1)


def test_markets_refresh_still_reloads_history():
    html = template_text()
    view = re.search(
        r"async function refreshMarketsFromView\(\) \{(.*?)\n\}",
        html, re.S)
    assert view, "refreshMarketsFromView missing"
    assert "refreshMarkets();" in view.group(1)
    assert "loadMarketsHistory();" in view.group(1)
    dispatch = re.search(
        r"function refreshCurrentView\(button\) \{(.*?)\n\}", html, re.S)
    assert dispatch, "refreshCurrentView missing"
    assert "refreshMarketsFromView();" in dispatch.group(1)
    assert "refreshNewsFromButton(button);" in dispatch.group(1)


NODE_PREAMBLE = """
const elements = {};
const document = { getElementById: (id) => elements[id] || null };
let newsViewReplaced = false;
function setView({ markets = 'none', weather = 'none', hub = 'none', replaced = false } = {}) {
    elements['refresh-btn'] = { textContent: '', style: { display: '' } };
    elements['markets-section'] = { style: { display: markets } };
    elements['weather-section'] = { style: { display: weather } };
    elements['morning-hub-section'] = { style: { display: hub } };
    newsViewReplaced = replaced;
}
"""

NODE_UPDATE_ASSERTIONS = """
setView();
updateRefreshButton();
assert.equal(elements['refresh-btn'].textContent, '\\u21bb Refresh news');
assert.equal(elements['refresh-btn'].style.display, '');
setView({ markets: 'block' });
updateRefreshButton();
assert.equal(elements['refresh-btn'].textContent, '\\u21bb Refresh markets');
assert.equal(elements['refresh-btn'].style.display, '');
setView({ weather: 'block' });
updateRefreshButton();
assert.equal(elements['refresh-btn'].style.display, 'none');
setView({ hub: 'block' });
updateRefreshButton();
assert.equal(elements['refresh-btn'].style.display, 'none');
setView({ replaced: true });
updateRefreshButton();
assert.equal(elements['refresh-btn'].style.display, 'none');
setView({ markets: 'block', replaced: true });
updateRefreshButton();
assert.equal(elements['refresh-btn'].textContent, '\\u21bb Refresh markets');
assert.equal(elements['refresh-btn'].style.display, '');
"""

NODE_DISPATCH_ASSERTIONS = """
const calls = [];
function refreshMarketsFromView() { calls.push('markets'); }
function refreshNewsFromButton(button) { calls.push('news:' + (button && button.id)); }
setView();
refreshCurrentView({ id: 'refresh-btn' });
assert.deepEqual(calls, ['news:refresh-btn']);
setView({ markets: 'block' });
refreshCurrentView({ id: 'refresh-btn' });
assert.deepEqual(calls, ['news:refresh-btn', 'markets']);
"""


def _run_node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def _extract(html, pattern, name):
    match = re.search(pattern, html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


def test_update_refresh_button_states_run_under_node():
    html = template_text()
    update = _extract(
        html, r"function updateRefreshButton\(\) \{(.*?)\n\}",
        "updateRefreshButton")
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + update
        + NODE_UPDATE_ASSERTIONS
    )
    _run_node(script)


def test_refresh_dispatch_runs_under_node():
    html = template_text()
    dispatch = _extract(
        html, r"function refreshCurrentView\(button\) \{(.*?)\n\}",
        "refreshCurrentView")
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + dispatch
        + NODE_DISPATCH_ASSERTIONS
    )
    _run_node(script)
