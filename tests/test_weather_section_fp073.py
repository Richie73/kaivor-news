"""FP073: weather section — Wirral by default, any place by search.

The weather section fetches Open-Meteo (free, no API key) directly from
the browser: current conditions plus a 3-day forecast for the local place
(Puddington, Wirral), a search box that finds any other place by name
(Open-Meteo geocoding), and recent places remembered in localStorage.

Most tests assert on the template source, following the codebase's
template-test pattern. test_weather_logic_runs_under_node goes further:
it extracts the FP073 JavaScript block and runs the pure helpers under
node, so a logic bug (like the FP067d regex that never matched) is
caught by execution, not by eyeballing strings. It skips where node is
not installed (e.g. a phone without node).
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
MAIN = Path(__file__).resolve().parents[1] / "main.py"

NODE_ASSERTIONS = """
assert.equal(weatherCodeInfo(0).text, 'Clear sky');
assert.equal(weatherCodeInfo(0).icon, '☀️');
assert.equal(weatherCodeInfo(55).text, 'Dense drizzle');
assert.equal(weatherCodeInfo(61).text, 'Slight rain');
assert.equal(weatherCodeInfo(95).icon, '⛈️');
assert.equal(weatherCodeInfo(999).text, 'Unknown');
assert.equal(windDirectionLabel(0), 'N');
assert.equal(windDirectionLabel(90), 'E');
assert.equal(windDirectionLabel(172), 'S');
assert.equal(windDirectionLabel(359), 'N');
assert.equal(windDirectionLabel(-45), 'NW');
const forecastUrl = buildForecastUrl(53.25332, -3.00877);
assert.ok(forecastUrl.startsWith('https://api.open-meteo.com/v1/forecast?'));
assert.ok(forecastUrl.includes('latitude=53.25332'));
assert.ok(forecastUrl.includes('longitude=-3.00877'));
assert.ok(forecastUrl.includes('forecast_days=7'));
const geocodeUrl = buildGeocodeUrl('London');
assert.ok(geocodeUrl.startsWith('https://geocoding-api.open-meteo.com/v1/search?'));
assert.ok(geocodeUrl.includes('name=London'));
assert.equal(formatPlaceName({ name: 'Paris', admin1: 'Île-de-France', country: 'France' }), 'Paris, Île-de-France, France');
assert.equal(formatPlaceName({ name: 'Chester', admin1: null, country: 'United Kingdom' }), 'Chester, United Kingdom');
assert.equal(dayLabel('2026-11-13', 0), 'Today');
assert.equal(dayLabel('2026-11-14', 1), 'Tomorrow');
assert.equal(typeof dayLabel('2026-11-15', 2), 'string');
assert.equal(WEATHER_DEFAULT_PLACE.name, 'Puddington, Wirral');
assert.equal(WEATHER_MAX_RECENT, 5);
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


def test_weather_section_markup_exists():
    html = template_text()
    assert 'id="weather-section"' in html
    assert 'id="weather-place"' in html
    assert 'id="weather-now"' in html
    assert 'id="weather-days"' in html
    assert 'id="weather-search-input"' in html
    assert 'id="weather-search-results"' in html
    assert 'id="weather-recent"' in html
    assert 'onclick="searchWeatherPlace()"' in html
    assert 'onclick="refreshWeather()"' in html


def test_default_place_is_puddington_wirral():
    js = weather_js_block()
    assert "name: 'Puddington, Wirral'" in js
    assert "latitude: 53.25332" in js
    assert "longitude: -3.00877" in js


def test_open_meteo_endpoints_are_used():
    js = weather_js_block()
    assert "https://api.open-meteo.com/v1/forecast?" in js
    assert "https://geocoding-api.open-meteo.com/v1/search?" in js
    assert "forecast_days: '7'" in js
    assert "current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m'" in js
    assert "daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'" in js


def test_wmo_code_mapping_covers_main_conditions():
    js = weather_js_block()
    for code, text in [
        (0, 'Clear sky'),
        (3, 'Overcast'),
        (55, 'Dense drizzle'),
        (61, 'Slight rain'),
        (65, 'Heavy rain'),
        (71, 'Slight snow'),
        (95, 'Thunderstorm'),
    ]:
        assert f"{code}: {{ text: '{text}'" in js


def test_recent_places_are_remembered_in_local_storage():
    js = weather_js_block()
    assert "WEATHER_RECENT_KEY = 'kaivor-weather-recent'" in js
    assert "WEATHER_LAST_KEY = 'kaivor-weather-last'" in js
    assert "WEATHER_MAX_RECENT = 5" in js
    assert "localStorage.getItem(WEATHER_RECENT_KEY)" in js
    assert "localStorage.setItem(WEATHER_LAST_KEY" in js


def test_weather_section_initializes_on_dom_ready():
    html = template_text()
    assert "initializeWeatherSection();" in html
    assert "function initializeWeatherSection()" in html
    assert "loadWeather(weatherLastPlace() || WEATHER_DEFAULT_PLACE)" in html


def test_fake_weather_removed_from_market_fallback():
    main = MAIN.read_text(encoding="utf-8")
    assert '"weather": "15°C"' not in main
    assert "'weather': \"15" not in main


def test_weather_logic_runs_under_node():
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
