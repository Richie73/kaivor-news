"""FP082: weather redesign — slim strip on home, full Weather category.

The tall weather card that pushed the news down the home page is split
in two: a slim one-line strip (place, temperature, condition, today's
summary — tap it to open the forecast) and the full forecast as its
own destination behind a 🌤️ Weather chip. The full view is polished:
a hero (big temperature, condition, feels-like, today's high/low), a
details grid (wind + gusts, humidity, rain, sunrise/sunset), the
one-line summary, the 12-hour strip, and the 7-day forecast as a
vertical list instead of a horizontal strip.

Navigation: showWeather() hides the news cards without destroying
them, so going back to any news category just shows them again (unlike
Chat/Saved, which replace the container). Every other view hides the
full weather view again via hideWeatherView().

Most tests assert on the template source, following the codebase's
template-test pattern. test_format_sun_time_runs_under_node executes
the new pure helper under node, like the FP073/FP074 node tests.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_ASSERTIONS = """
assert.equal(formatSunTime('2026-11-14T07:12'), '07:12');
assert.equal(formatSunTime('2026-11-14T16:08'), '16:08');
assert.equal(formatSunTime(null), '');
assert.equal(formatSunTime(''), '');
const url82 = buildForecastUrl(53.25332, -3.00877);
assert.ok(url82.includes('sunrise'));
assert.ok(url82.includes('sunset'));
"""


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def weather_js_block():
    html = template_text()
    match = re.search(
        r"// FP073 WEATHER: BEGIN(.*?)// FP073 WEATHER: END",
        html,
        re.S,
    )
    assert match, "FP073 weather JS block markers missing"
    return match.group(1)


def show_weather_body():
    html = template_text()
    start = html.index("function showWeather(element) {")
    end = html.index("function hideWeatherView()", start)
    return html[start:end]


def test_weather_button_is_in_the_bottom_nav():
    # FP084: the Weather chip left the rail for the bottom nav.
    html = template_text()
    assert '<button type="button" id="nav-weather" class="nav-item" data-nav="weather" onclick="showWeather(this)">' in html
    assert 'id="weather-chip"' not in html


def test_slim_strip_markup_exists():
    html = template_text()
    assert 'id="weather-strip"' in html
    assert 'class="weather-strip"' in html
    assert "onclick=\"showWeather(document.getElementById('nav-weather'))\"" in html
    assert 'id="weather-strip-place"' in html
    assert 'id="weather-strip-now"' in html
    assert 'id="weather-strip-summary"' in html
    assert 'class="weather-strip-open"' in html
    strip = re.search(r"\.weather-strip \{(.*?)\}", html, re.S)
    assert strip
    assert "display:flex" in strip.group(1).replace(" ", "")


def test_full_view_is_hidden_until_opened():
    html = template_text()
    assert '<section id="weather-section" class="weather-card" aria-label="Weather" style="display:none">' in html
    assert 'id="weather-now"' in html
    assert 'id="weather-details"' in html
    assert 'id="weather-summary"' in html
    assert 'id="weather-hourly"' in html
    assert 'id="weather-days"' in html
    assert 'id="weather-search-input"' in html


def test_show_weather_hides_cards_without_destroying_them():
    body = show_weather_body()
    assert "querySelectorAll('.card')" in body
    assert "style.display = 'none'" in body
    assert "section.style.display = 'block'" in body
    assert "strip.style.display = 'none'" in body
    assert "'Weather'" in body
    assert "innerHTML" not in body


def test_other_views_hide_the_weather_view():
    html = template_text()
    for opener in [
        "function filterCategory(category, element) {",
        "async function showSaved(element) {",
        "function showChat(element) {",
        "async function showRelevanceProfile(element){",
    ]:
        start = html.index(opener)
        window = html[start:start + len(opener) + 40]
        assert "hideWeatherView();" in window, opener
    assert html.count("hideWeatherView();") == 4  # one call site per other view


def test_weather_is_not_a_swipe_destination():
    # FP084: swiping moves between news categories only; Weather is
    # reached from the bottom nav bar (or by tapping the strip).
    html = template_text()
    match = re.search(r"const swipeCategories = \(\) => Array\.from\(document\.querySelectorAll\((.*?)\)\);", html, re.S)
    assert match
    assert 'showWeather(' not in match.group(1)
    assert 'filterCategory(' in match.group(1)


def test_forecast_request_asks_for_sunrise_and_sunset():
    js = weather_js_block()
    assert "sunrise,sunset" in js
    assert "daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset'" in js


def test_hero_and_details_are_rendered():
    js = weather_js_block()
    for fragment in [
        "weather-hero",
        "weather-hero-temp",
        "weather-hero-condition",
        "weather-hero-sub",
        "Feels like ",
        "High ",
        "Low ",
        "weather-detail",
        "Wind",
        "Humidity",
        "Rain",
        "Sun",
        "formatSunTime(data.daily.sunrise[0])",
        "formatSunTime(data.daily.sunset[0])",
    ]:
        assert fragment in js, fragment


def test_strip_renders_from_the_same_forecast():
    js = weather_js_block()
    assert "stripNowEl.textContent = icon + ' ' + temp + '° ' + info.text" in js
    assert "stripSummaryEl.textContent = summary" in js
    assert "const summary = weatherSummary(data.hourly.time, data.hourly.precipitation_probability, start, 12)" in js


def test_days_render_as_list_rows():
    js = weather_js_block()
    for fragment in [
        "weather-day-row",
        "weather-day-row-name",
        "weather-day-row-icon",
        "weather-day-row-rain",
        "weather-day-row-temp",
        "dayLabel(isoDate, index)",
    ]:
        assert fragment in js, fragment


def test_format_sun_time_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    js = weather_js_block()
    script = "import assert from 'node:assert/strict';\n" + js + NODE_ASSERTIONS
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        script_path = handle.name
    try:
        result = subprocess.run(
            [node, script_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
