"""FP119: rain radar in the Weather view.

A Leaflet map centred on Puddington with RainViewer's radar
overlay (free, no key): the latest frame on load, and a Play
button that steps through the past ~2 hours so Richie can see
rain heading for site. The map loads lazily on the first
Weather view; playback stops when the view is left.
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


def test_leaflet_assets_present():
    html = _template_text()
    assert 'href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"' in html
    assert 'src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"' in html
    # Both assets carry subresource integrity hashes (computed from
    # the files unpkg serves) so a tampered CDN copy cannot run.
    css = re.search(r'<link rel="stylesheet" href="https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css"[^>]*>', html)
    js = re.search(r'<script src="https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js"[^>]*>', html)
    assert css is not None and 'integrity="sha384-' in css.group(0)
    assert js is not None and 'integrity="sha384-' in js.group(0)
    # The Leaflet script loads before the page's own inline script.
    assert html.index("leaflet@1.9.4/dist/leaflet.js") < html.index("<script>\n")


def test_radar_markup():
    html = _template_text()
    assert 'id="rain-radar-map"' in html
    assert 'id="rain-radar-play"' in html
    assert 'onclick="toggleRainRadarPlayback()"' in html
    assert 'id="rain-radar-time"' in html
    assert 'id="rain-radar-note"' in html
    assert "Rain radar" in html
    assert "RAINVIEWER_MAPS_URL = 'https://api.rainviewer.com/public/weather-maps.json'" in html
    assert "async function loadRainRadar(force)" in html
    assert "function toggleRainRadarPlayback()" in html
    assert "function stopRainRadarPlayback()" in html


def test_radar_hooks():
    html = _template_text()
    start = html.index("function showWeather(element) {")
    window = html[start:start + 1500]
    assert "loadRainRadar();" in window
    start = html.index("function hideWeatherView() {")
    window = html[start:start + 400]
    assert "stopRainRadarPlayback();" in window
    start = html.index("function refreshWeather() {")
    window = html[start:start + 400]
    assert "loadRainRadar(true);" in window


def test_radar_css_uses_tokens():
    html = _template_text()
    style = html[html.index("<style>"):html.index("</style>")]
    assert "#rain-radar-map { height:260px; border-radius:var(--radius-md); margin-top:var(--space-sm); }" in style
    assert ".rain-radar-controls { display:flex; align-items:center; gap:var(--space-sm); margin-top:var(--space-sm); }" in style
    assert ".rain-radar-time { font-size:var(--text-sm); color:var(--muted); }" in style
    assert ".rain-radar-note { font-size:var(--text-sm); color:var(--faint); margin:var(--space-sm) 0 0; }" in style


def test_radar_helpers_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    url_match = re.search(r"function rainRadarTileUrl\(path, z, x, y\) \{(.*?)\n\}", html, re.S)
    label_match = re.search(r"function rainRadarFrameLabel\(epochSeconds\) \{(.*?)\n\}", html, re.S)
    next_match = re.search(r"function rainRadarNextIndex\(index, total\) \{(.*?)\n\}", html, re.S)
    assert url_match is not None
    assert label_match is not None
    assert next_match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        + url_match.group(0)
        + "\n"
        + label_match.group(0)
        + "\n"
        + next_match.group(0)
        + "\nassert.strictEqual(rainRadarTileUrl('/v2/radar/abc', 7, 63, 41), 'https://tilecache.rainviewer.com/v2/radar/abc/256/7/63/41/2/1_1.png');\n"
        + "const label = rainRadarFrameLabel(1794949800);\n"
        + "assert.match(label, /^\\d{2}:\\d{2}$/);\n"
        + "const tenLater = rainRadarFrameLabel(1794949800 + 600);\n"
        + "const mins = (s) => Number(s.slice(0, 2)) * 60 + Number(s.slice(3, 5));\n"
        + "assert.strictEqual((mins(tenLater) - mins(label) + 1440) % 1440, 10);\n"
        + "assert.strictEqual(rainRadarNextIndex(0, 12), 1);\n"
        + "assert.strictEqual(rainRadarNextIndex(11, 12), 0);\n"
        + "assert.strictEqual(rainRadarNextIndex(0, 0), 0);\n"
        + "assert.strictEqual(rainRadarNextIndex(5, 1), 0);\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
