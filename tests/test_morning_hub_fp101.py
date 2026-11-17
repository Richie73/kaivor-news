"""FP101: the morning hub — one place to start the day.

A sixth bottom-nav destination (🌅 Hub, first in the bar): a
time-aware greeting, the weather now (reusing the last forecast
already fetched — no second call), the top five stories (read
from the news cards already on the page) and a market snapshot
from /api/ticker. Calendar and live travel are NOT in v1 — they
need the Google account connected to Kaivor.

The hub hides the news cards without destroying them, like the
weather and markets views, so every other view must hide it.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
READING_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "reading.html"

NODE_ASSERTIONS = """
const assert = require('assert');
assert.equal(morningGreeting(2), 'Good night');
assert.equal(morningGreeting(5), 'Good morning');
assert.equal(morningGreeting(8), 'Good morning');
assert.equal(morningGreeting(11), 'Good morning');
assert.equal(morningGreeting(12), 'Good afternoon');
assert.equal(morningGreeting(17), 'Good afternoon');
assert.equal(morningGreeting(18), 'Good evening');
assert.equal(morningGreeting(22), 'Good evening');
assert.equal(morningGreeting(23), 'Good night');
assert.equal(morningGreeting(0), 'Good night');
"""


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(rf"function {name}\(.*?\n\}}", html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


def test_hub_nav_item():
    html = template_text()
    assert (
        '<button type="button" id="nav-hub" class="nav-item" data-nav="hub" '
        'onclick="showMorningHub(this)"><span class="nav-icon">🌅</span><span>Hub</span></button>'
        in html
    )
    reading = READING_TEMPLATE.read_text(encoding="utf-8")
    assert 'href="/#hub"' in reading
    assert 'data-nav="hub"' in reading


def test_hub_section_exists():
    html = template_text()
    assert '<section id="morning-hub-section" aria-label="Morning hub" style="display:none">' in html
    assert 'id="hub-greeting"' in html
    assert 'id="hub-date"' in html
    assert 'id="hub-weather"' in html
    assert 'id="hub-stories"' in html
    assert 'id="hub-markets"' in html


def test_morning_greeting_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    match = re.search(r"function morningGreeting\(hour\) \{.*?\n\}", html, re.S)
    assert match
    script = match.group(0) + "\n" + NODE_ASSERTIONS
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_show_hub_hides_other_views_and_renders():
    html = template_text()
    body = function_body(html, "showMorningHub")
    assert "hideWeatherView();" in body
    assert "hideMarketsView();" in body
    assert "getElementById('morning-hub-section')" in body
    assert "section.style.display = 'block'" in body
    assert "renderMorningHub();" in body
    assert "'Morning hub'" in body


def test_other_views_hide_the_hub():
    html = template_text()
    for opener in [
        "function filterCategory(category, element) {",
        "async function showSaved(element) {",
        "function showChat(element) {",
        "function showSettings(element){",
        "function showWeather(element) {",
        "function showMarkets() {",
        "function showReceipts() {",
        "function showRams() {",
        "async function showMemories() {",
        "async function showTasks() {",
    ]:
        start = html.index(opener)
        window = html[start:start + len(opener) + 120]
        assert "hideMorningHubView();" in window, opener
    assert html.count("hideMorningHubView();") == 10  # FP114: showTasks joined


def test_hub_deep_link():
    html = template_text()
    assert "else if (initialHash === '#hub') { showMorningHub(document.getElementById('nav-hub')); }" in html


def test_hub_reuses_weather_stories_and_ticker():
    html = template_text()
    # Weather: the last conditions are stored when a forecast renders.
    assert "let weatherLastNow = null;" in html
    assert "weatherLastNow = {place: place.name, temp, feels, condition: info.text, icon, high: todayHigh, low: todayLow, summary: ''};" in html
    assert "if (weatherLastNow) weatherLastNow.summary = summary;" in html
    # Stories: read from the news cards already on the page (or the
    # cached news HTML when another view has replaced the container).
    body = function_body(html, "morningTopStories")
    assert ".card[data-article-id] h3 a" in body
    assert "cachedNewsHtml" in body
    assert "slice(0, 5)" in body
    # Markets: a fresh ticker fetch, three picks, reusing the
    # markets price formatter.
    markets_body = function_body(html, "loadMorningHubMarkets")
    assert "fetch('/api/ticker', {cache: 'no-store'})" in markets_body
    assert "formatMarketPrice(key, ticker[key])" in markets_body
    assert "['Gold', 'Gold'], ['Bitcoin', 'Bitcoin'], ['GBP_USD', '£ → $']" in markets_body
