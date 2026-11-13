"""FP074: weather upgrades — hourly strip, wind gusts, 7-day forecast,
one-line summary.

Extends the FP073 weather section: the forecast request now asks for
hourly temperature/rain-chance/condition plus wind gusts and 7 days
instead of 3; the section shows the next 12 hours as a scrollable
strip, gusts in the current details, a 7-day scrollable strip, and a
one-line summary ("Dry until 14:00, then rain.") derived from the
hourly rain chances.

The summary and hour-slicing helpers are pure functions in the same
FP073-marked JavaScript block, covered by the node logic test below
(the FP073 test's node run still covers the original helpers).
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

NODE_ASSERTIONS = """
const times = ['2026-11-13T20:00','2026-11-13T21:00','2026-11-13T22:00','2026-11-13T23:00','2026-11-14T00:00','2026-11-14T01:00','2026-11-14T02:00','2026-11-14T03:00','2026-11-14T04:00','2026-11-14T05:00','2026-11-14T06:00','2026-11-14T07:00','2026-11-14T08:00'];
assert.equal(weatherSummary(times, [0,0,0,0,0,0,0,0,0,0,0,0,0], 0, 12), 'Dry for the next 12 hours.');
assert.equal(weatherSummary(times, [80,80,80,10,0,0,0,0,0,0,0,0,0], 0, 12), 'Rain now, easing by 23:00.');
assert.equal(weatherSummary(times, [0,0,0,0,0,80,80,80,0,0,0,0,0], 0, 12), 'Dry until 01:00, then rain.');
assert.equal(weatherSummary(times, [80,80,80,80,80,80,80,80,80,80,80,80,80], 0, 12), 'Rain for the next 12 hours.');
assert.equal(weatherSummary(times, [0,0,0,0,0,0,0,0,0,0,0,0,0], 99, 12), '');
assert.equal(hourlyStartIndex(times, '2026-11-13T20:00'), 0);
assert.equal(hourlyStartIndex(times, '2026-11-13T22:00'), 2);
assert.equal(hourlyStartIndex(times, '2026-11-13T20:15'), 1);
assert.equal(hourlyStartIndex(times, null), 0);
const url = buildForecastUrl(53.25332, -3.00877);
assert.ok(url.includes('forecast_days=7'));
assert.ok(url.includes('wind_gusts_10m'));
assert.ok(url.includes('hourly=temperature_2m'));
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
    assert match, "weather JS block markers missing"
    return match.group(1)


def test_forecast_request_asks_for_hourly_gusts_and_seven_days():
    js = weather_js_block()
    assert "wind_gusts_10m" in js
    assert "hourly: 'temperature_2m,precipitation_probability,weather_code'" in js
    assert "forecast_days: '7'" in js


def test_hourly_strip_and_summary_markup_exist():
    html = template_text()
    assert 'id="weather-summary"' in html
    assert 'id="weather-hourly"' in html
    assert 'Next 12 hours' in html
    assert '7-day forecast' in html


def test_days_strip_scrolls_horizontally():
    html = template_text()
    match = re.search(r"\.weather-days \{(.*?)\}", html, re.S)
    assert match
    assert "overflow-x:auto" in match.group(1).replace(" ", "")
    day = re.search(r"\.weather-day \{(.*?)\}", html, re.S)
    assert day
    assert "flex:0 0 auto" in day.group(1)


def test_gusts_shown_in_current_details():
    js = weather_js_block()
    assert "wind_gusts_10m" in js
    assert "' (gusts ' + gusts + ')'" in js


def test_hourly_rendering_uses_next_twelve_hours():
    js = weather_js_block()
    assert "hourlyStartIndex(data.hourly.time, current.time)" in js
    assert "data.hourly.time.slice(start, start + 12)" in js
    assert "weatherSummary(data.hourly.time, data.hourly.precipitation_probability, start, 12)" in js


def test_weather_upgrade_logic_runs_under_node():
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
