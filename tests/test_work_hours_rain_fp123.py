"""FP123: a work-hours rain line in the Weather view.

One plain sentence about rain during work hours (07:00-17:00)
— today, or tomorrow once today's work hours are over. It
uses the hourly rain chances already fetched, with the same
50% "likely" threshold weatherSummary uses. Each hourly value
covers its own hour, so wet hours 10, 11, 12 read as
10:00-13:00, and a line ends with "Dry after …" when the rain
clears before 17:00.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_work_rain_markup_and_hooks():
    html = _template_text()
    assert 'id="weather-work-rain"' in html
    assert "function workHoursRainLine(times, rainChances, nowIso) {" in html
    assert "workHoursRainLine(data.hourly.time, data.hourly.precipitation_probability, current.time)" in html
    start = html.index("async function loadWeather(")
    window = html[start:start + 2500]
    assert "if (workRainEl) workRainEl.textContent = '';" in window


def _node_script(html):
    consts = re.search(
        r"const WORK_HOURS_START = 7;\nconst WORK_HOURS_END = 17;\nconst WORK_RAIN_THRESHOLD = 50;",
        html,
    )
    func = re.search(r"function workHoursRainLine\(times, rainChances, nowIso\) \{(.*?)\n\}", html, re.S)
    assert consts is not None
    assert func is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + consts.group(0)
        + "\n"
        + func.group(0)
        + "\nfunction hoursFor(date, wetHours, wetValue) {\n"
        + "  const times = [];\n"
        + "  const probs = [];\n"
        + "  for (let h = 0; h < 24; h++) {\n"
        + "    times.push(date + 'T' + String(h).padStart(2, '0') + ':00');\n"
        + "    probs.push(wetHours.includes(h) ? (wetValue || 80) : 10);\n"
        + "  }\n"
        + "  return [times, probs];\n"
        + "}\n"
    )
    return script


def test_work_hours_rain_line_today_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    script = _node_script(_template_text())
    script += (
        "let [t, p] = hoursFor('2026-11-18', [10, 11, 12]);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: rain likely 10:00\u201313:00. Dry after 13:00.');\n"
        "[t, p] = hoursFor('2026-11-18', []);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: no rain expected during work hours.');\n"
        "[t, p] = hoursFor('2026-11-18', [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: rain likely all work hours (07:00\u201317:00).');\n"
        "[t, p] = hoursFor('2026-11-18', [9, 14]);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: rain likely 09:00\u201310:00 and 14:00\u201315:00. Dry after 15:00.');\n"
        "[t, p] = hoursFor('2026-11-18', [15, 16]);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: rain likely 15:00\u201317:00.');\n"
        "[t, p] = hoursFor('2026-11-18', [12], 50);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: rain likely 12:00\u201313:00. Dry after 13:00.');\n"
        "[t, p] = hoursFor('2026-11-18', [12], 49);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T06:00'), 'Today: no rain expected during work hours.');\n"
        "[t, p] = hoursFor('2026-11-18', [8, 12]);\n"
        "assert.strictEqual(workHoursRainLine(t, p, '2026-11-18T10:30'), 'Today: rain likely 12:00\u201313:00. Dry after 13:00.');\n"
        "assert.strictEqual(workHoursRainLine([], [], '2026-11-18T06:00'), '');\n"
        "assert.strictEqual(workHoursRainLine(null, null, '2026-11-18T06:00'), '');\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr


def test_work_hours_rain_line_tomorrow_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    script = _node_script(_template_text())
    script += (
        "const [t1, p1] = hoursFor('2026-11-18', []);\n"
        "const [t2, p2] = hoursFor('2026-11-19', [8, 9]);\n"
        "assert.strictEqual(workHoursRainLine(t1.concat(t2), p1.concat(p2), '2026-11-18T19:00'), 'Tomorrow: rain likely 08:00\u201310:00. Dry after 10:00.');\n"
        "const [t3, p3] = hoursFor('2026-11-19', []);\n"
        "assert.strictEqual(workHoursRainLine(t1.concat(t3), p1.concat(p3), '2026-11-18T19:00'), 'Tomorrow: no rain expected during work hours.');\n"
        "const [t4, p4] = hoursFor('2026-11-19', [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]);\n"
        "assert.strictEqual(workHoursRainLine(t1.concat(t4), p1.concat(p4), '2026-11-18T23:30'), 'Tomorrow: rain likely all work hours (07:00\u201317:00).');\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
