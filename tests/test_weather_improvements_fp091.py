"""FP091: weather improvements — attribution, air quality, saved
places, 24-hour strip, 16-day option.

- The Weather view credits Open-Meteo with a link (CC BY 4.0 asks
  for a link, not just text) and credits the air-quality API too.
- Air quality comes from Open-Meteo's air-quality API (free, no
  key): European AQI + PM2.5 in the details grid. The call runs
  after the forecast and can never break it.
- Saved places: the user keeps their own list (up to 10) in
  localStorage, separate from automatic recents. Save from the
  hero button, tap a saved place to load it, rename inline,
  remove, or reorder with up/down.
- The hourly strip and the one-line summary now cover 24 hours
  (was 12). The daily forecast is fetched as 16 days but shown
  as 7 by default, with a toggle to reveal the rest.

The pure helpers are executed under node (same pattern as FP073);
the rest asserts on the template source.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_ASSERTIONS = """
const aqUrl = buildAirQualityUrl(53.25332, -3.00877);
assert.ok(aqUrl.startsWith('https://air-quality-api.open-meteo.com/v1/air-quality?'));
assert.ok(aqUrl.includes('latitude=53.25332'));
assert.ok(aqUrl.includes('longitude=-3.00877'));
assert.ok(aqUrl.includes('current=european_aqi'));
assert.ok(aqUrl.includes('pm2_5'));
assert.equal(aqiLabel(0), 'Good');
assert.equal(aqiLabel(19), 'Good');
assert.equal(aqiLabel(20), 'Fair');
assert.equal(aqiLabel(34), 'Fair');
assert.equal(aqiLabel(40), 'Moderate');
assert.equal(aqiLabel(60), 'Poor');
assert.equal(aqiLabel(80), 'Very poor');
assert.equal(aqiLabel(100), 'Extremely poor');
assert.equal(aqiLabel(150), 'Extremely poor');
assert.equal(aqiLabel(null), '');
assert.equal(aqiLabel('abc'), '');
const pudd = { name: 'Puddington, Wirral', latitude: 53.25332, longitude: -3.00877 };
const chester = { name: 'Chester', latitude: 53.19, longitude: -2.89 };
const london = { name: 'London', latitude: 51.5, longitude: -0.12 };
assert.equal(weatherSavedPlaceKey(pudd), '53.25332,-3.00877');
assert.equal(WEATHER_MAX_SAVED, 10);
let saved = addSavedPlace([], pudd);
assert.equal(saved.length, 1);
assert.equal(saved[0].name, 'Puddington, Wirral');
saved = addSavedPlace(saved, chester);
assert.equal(saved[0].name, 'Chester');
assert.equal(saved.length, 2);
saved = addSavedPlace(saved, pudd);
assert.equal(saved.length, 2);
assert.equal(saved[0].name, 'Puddington, Wirral');
const capped = addSavedPlace([pudd, chester], london, 2);
assert.equal(capped.length, 2);
assert.equal(capped[0].name, 'London');
const removed = removeSavedPlace([pudd, chester, london], weatherSavedPlaceKey(chester));
assert.equal(removed.length, 2);
assert.equal(removed[0].name, 'Puddington, Wirral');
const renamed = renameSavedPlace([pudd], weatherSavedPlaceKey(pudd), 'Home');
assert.equal(renamed[0].name, 'Home');
assert.equal(renameSavedPlace([pudd], weatherSavedPlaceKey(pudd), '   ')[0].name, 'Puddington, Wirral');
const movedDown = moveSavedPlace([pudd, chester, london], weatherSavedPlaceKey(pudd), 1);
assert.equal(movedDown[1].name, 'Puddington, Wirral');
const movedUp = moveSavedPlace([pudd, chester, london], weatherSavedPlaceKey(london), -1);
assert.equal(movedUp[1].name, 'London');
assert.deepEqual(moveSavedPlace([pudd, chester], weatherSavedPlaceKey(pudd), -1), [pudd, chester]);
assert.deepEqual(moveSavedPlace([pudd, chester], weatherSavedPlaceKey(chester), 1), [pudd, chester]);
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


def test_weather_improvements_logic_runs_under_node():
    if not shutil.which("node"):
        pytest.skip("node is not installed")
    script = (
        "const assert = require('assert');\n"
        + weather_js_block()
        + "\n"
        + NODE_ASSERTIONS
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".js", delete=False
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run(
        ["node", path], capture_output=True, text=True, timeout=30
    )
    Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr or result.stdout


def test_attribution_link_present():
    html = template_text()
    assert 'class="weather-credit"' in html
    assert '<a href="https://open-meteo.com" target="_blank" rel="noopener noreferrer">Open-Meteo</a>' in html
    assert 'https://open-meteo.com/en/docs/air-quality-api' in html


def test_save_place_button_and_saved_container():
    html = template_text()
    assert 'id="weather-save-place"' in html
    assert 'onclick="toggleSaveWeatherPlace()"' in html
    assert 'id="weather-saved"' in html
    assert 'class="weather-saved"' in html


def test_air_quality_cells_in_details():
    js = weather_js_block()
    assert 'id="weather-aqi-value"' in js
    assert 'id="weather-pm25-value"' in js
    assert 'Air quality' in js
    assert 'PM2.5' in js
    assert 'function loadAirQuality(place)' in js
    assert 'buildAirQualityUrl(place.latitude, place.longitude)' in js


def test_load_weather_fetches_air_quality_and_renders_saved():
    js = weather_js_block()
    start = js.index('async function loadWeather(place)')
    end = js.index('async function loadAirQuality(place)')
    body = js[start:end]
    assert 'loadAirQuality(place);' in body
    assert 'renderSavedPlaces();' in body
    assert 'updateSaveWeatherPlaceButton();' in body


def test_24_hour_strip_and_16_day_toggle():
    html = template_text()
    js = weather_js_block()
    assert 'Next 24 hours' in html
    assert 'id="weather-days-toggle"' in html
    assert 'onclick="toggleWeatherDays()"' in html
    assert 'Show 16 days' in html
    assert 'data.hourly.time.slice(start, start + 24)' in js
    assert 'weatherSummary(data.hourly.time, data.hourly.precipitation_probability, start, 24)' in js
    assert "forecast_days: '16'" in js
    assert 'function renderWeatherDays()' in js
    assert 'function toggleWeatherDays()' in js


def test_saved_places_functions_exist():
    js = weather_js_block()
    for name in [
        'function weatherSavedPlaceKey(place)',
        'function addSavedPlace(saved, place, max)',
        'function removeSavedPlace(saved, key)',
        'function renameSavedPlace(saved, key, newName)',
        'function moveSavedPlace(saved, key, direction)',
        'function weatherSavedPlaces()',
        'function toggleSaveWeatherPlace()',
        'function renderSavedPlaces()',
    ]:
        assert name in js


def test_days_skip_missing_data():
    # FP089.2 (found in FP091's live check): Open-Meteo's 16th day
    # can arrive with null values — the row is skipped rather than
    # showing a ❓ icon with 0° / 0°.
    js = weather_js_block()
    assert 'if (maxRaw === null || maxRaw === undefined || isNaN(Number(maxRaw))) return \'\';' in js
