"""FP106: Met Office Weather Warnings for Puddington.

Reads the NSWWS API: an Atom feed entry point, then the GeoJSON
"issued" collection it links to (rel="related"). Warnings are
filtered to the ones whose polygon covers Puddington
(point-in-polygon on the MultiPolygon outer rings). Shown in the
Weather view, the morning hub, and the morning brief text.
Both signup routes (v1.0 contact form, v1.1 DataHub) give the same
shape, so both auth headers are sent. Docs verified 16 Nov 2026.
"""
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests

import main
import morning_brief
import weather_warnings
from weather_warnings import (
    WarningsError,
    fetch_warnings,
    get_warnings,
    parse_atom_related_link,
    parse_warnings,
    point_in_multipolygon,
    point_in_polygon,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

# A box around the Wirral, in [lon, lat] GeoJSON order.
WIRRAL_RING = [[-3.2, 53.2], [-2.9, 53.2], [-2.9, 53.35], [-3.2, 53.35], [-3.2, 53.2]]
SCOTLAND_RING = [[-4.5, 58.0], [-4.0, 58.0], [-4.0, 58.5], [-4.5, 58.5], [-4.5, 58.0]]

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>NSWWS</title>
  <link rel="self" href="https://example.com/feed"/>
  <link rel="related" href="https://example.com/v1.0/objects/issued/uuid-1"/>
  <updated>2026-11-16T07:00:00Z</updated>
  <entry><title>Warning 1</title></entry>
</feed>
"""


def feature(level, ring, valid_from="2026-11-16T10:00:00Z", headline="Rain warning"):
    return {
        "type": "Feature",
        "properties": {
            "issuedDate": "2026-11-16T07:00:00Z",
            "weatherType": ["RAIN"],
            "warningLikelihood": 3,
            "warningLevel": level,
            "warningStatus": "ISSUED",
            "warningHeadline": headline,
            "whatToExpect": ["Flooding possible", "Delays to travel"],
            "warningId": f"id-{level}",
            "warningFurtherDetails": "Heavy rain expected.",
            "modifiedDate": "2026-11-16T07:00:00Z",
            "validFromDate": valid_from,
            "affectedAreas": [{"regionName": "North West England", "regionCode": "NW", "subRegions": ["Cheshire West and Chester"]}],
            "warningImpact": 2,
            "validToDate": "2026-11-16T22:00:00Z",
        },
        "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]},
    }


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(rf"function {name}\(.*?\n\}}", html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


class FakeResponse:
    def __init__(self, text="", payload=None, status_code=200, bad_json=False):
        self.text = text
        self._payload = payload
        self.status_code = status_code
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


# --- geometry ---

def test_point_in_polygon_inside_and_outside():
    assert point_in_polygon(53.25332, -3.00877, WIRRAL_RING) is True
    assert point_in_polygon(53.25332, -2.5, WIRRAL_RING) is False
    assert point_in_polygon(54.0, -3.00877, WIRRAL_RING) is False
    assert point_in_polygon(53.25332, -3.00877, [[-3.2, 53.2]]) is False


def test_point_in_multipolygon_checks_each_polygon():
    multi = [[SCOTLAND_RING], [WIRRAL_RING]]
    assert point_in_multipolygon(53.25332, -3.00877, multi) is True
    assert point_in_multipolygon(53.25332, -3.00877, [[SCOTLAND_RING]]) is False
    assert point_in_multipolygon(53.25332, -3.00877, []) is False


# --- Atom feed ---

def test_parse_atom_related_link():
    assert parse_atom_related_link(SAMPLE_FEED) == "https://example.com/v1.0/objects/issued/uuid-1"


def test_parse_atom_related_link_errors():
    try:
        parse_atom_related_link("<feed></feed>")
    except WarningsError as exc:
        assert "no latest-warnings link" in str(exc)
    else:
        raise AssertionError("missing link must raise")
    try:
        parse_atom_related_link("not xml at all <")
    except WarningsError as exc:
        assert "not valid XML" in str(exc)
    else:
        raise AssertionError("bad XML must raise")


# --- parsing ---

def test_parse_warnings_filters_to_puddington():
    collection = {
        "type": "FeatureCollection",
        "features": [
            feature("YELLOW", WIRRAL_RING),
            feature("AMBER", SCOTLAND_RING, headline="Scotland warning"),
            {"type": "Feature", "properties": {"warningLevel": "RED"}, "geometry": {"type": "Point", "coordinates": [-3.0, 53.25]}},
        ],
    }
    warnings = parse_warnings(collection)
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning["level"] == "YELLOW"
    assert warning["types"] == ["RAIN"]
    assert warning["headline"] == "Rain warning"
    assert warning["valid_from"] == "2026-11-16T10:00:00Z"
    assert warning["valid_to"] == "2026-11-16T22:00:00Z"
    assert warning["areas"] == ["North West England"]
    assert warning["what_to_expect"] == ["Flooding possible", "Delays to travel"]


def test_parse_warnings_sorts_by_level_then_date():
    collection = {
        "type": "FeatureCollection",
        "features": [
            feature("YELLOW", WIRRAL_RING, valid_from="2026-11-16T10:00:00Z"),
            feature("RED", WIRRAL_RING, valid_from="2026-11-17T10:00:00Z", headline="Red warning"),
            feature("AMBER", WIRRAL_RING, valid_from="2026-11-16T09:00:00Z"),
            feature("YELLOW", WIRRAL_RING, valid_from="2026-11-16T08:00:00Z", headline="Earlier yellow"),
        ],
    }
    warnings = parse_warnings(collection)
    assert [w["level"] for w in warnings] == ["RED", "AMBER", "YELLOW", "YELLOW"]
    assert warnings[2]["headline"] == "Earlier yellow"


# --- fetching ---

def test_fetch_warnings_not_configured():
    assert fetch_warnings("", "") == {"status": "not_configured"}
    assert fetch_warnings("https://example.com/feed", "") == {"status": "not_configured"}
    assert fetch_warnings("", "key") == {"status": "not_configured"}


def test_fetch_warnings_full_chain():
    collection = {"type": "FeatureCollection", "features": [feature("YELLOW", WIRRAL_RING)]}
    seen = []

    def fake_get(url, headers=None, timeout=None):
        seen.append((url, headers))
        if url == "https://example.com/feed":
            return FakeResponse(text=SAMPLE_FEED)
        return FakeResponse(payload=collection)

    with patch.object(weather_warnings.requests, "get", side_effect=fake_get):
        result = fetch_warnings("https://example.com/feed", "test-key")
    assert result["status"] == "ok"
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["level"] == "YELLOW"
    assert seen[0][0] == "https://example.com/feed"
    assert seen[1][0] == "https://example.com/v1.0/objects/issued/uuid-1"
    assert seen[0][1] == {"x-api-key": "test-key", "apikey": "test-key"}


def test_fetch_warnings_errors():
    with patch.object(
        weather_warnings.requests, "get", return_value=FakeResponse(status_code=403)
    ):
        result = fetch_warnings("https://example.com/feed", "bad-key")
    assert result["status"] == "error"
    assert "refused the warnings key" in result["error"]
    with patch.object(
        weather_warnings.requests, "get", side_effect=requests.RequestException("down")
    ):
        assert fetch_warnings("https://example.com/feed", "key")["status"] == "error"
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(text=SAMPLE_FEED)
        return FakeResponse(payload=None, bad_json=True)

    with patch.object(weather_warnings.requests, "get", side_effect=fake_get):
        result = fetch_warnings("https://example.com/feed", "key")
    assert result["status"] == "error"


def test_get_warnings_caches(monkeypatch):
    monkeypatch.setattr(weather_warnings, "_WARNINGS_CACHE", {"data": None, "fetched_at": 0})
    collection = {"type": "FeatureCollection", "features": []}

    def fake_get(url, headers=None, timeout=None):
        if url == "https://example.com/feed":
            return FakeResponse(text=SAMPLE_FEED)
        return FakeResponse(payload=collection)

    with patch.object(weather_warnings.requests, "get", side_effect=fake_get) as get:
        first = get_warnings("https://example.com/feed", "key")
        second = get_warnings("https://example.com/feed", "key")
    assert first == second
    assert get.call_count == 2  # feed + GeoJSON once; second call served from cache


# --- morning brief ---

def test_brief_warning_lines():
    from morning_brief import brief_warning_lines

    result = {"status": "ok", "warnings": parse_warnings({"type": "FeatureCollection", "features": [feature("AMBER", WIRRAL_RING, headline="Heavy rain")]})}
    lines = brief_warning_lines(result)
    assert lines == ["\u26a0\ufe0f AMBER RAIN \u2014 Heavy rain"]
    assert brief_warning_lines({"status": "not_configured"}) == []
    assert brief_warning_lines({"status": "error"}) == []


def test_build_morning_brief_includes_warnings():
    now = datetime(2026, 11, 16, 7, 0, tzinfo=morning_brief.LONDON)
    warnings_result = {"status": "ok", "warnings": parse_warnings({"type": "FeatureCollection", "features": [feature("YELLOW", WIRRAL_RING)]})}
    brief = morning_brief.build_morning_brief(now, [], {}, {}, {}, {"status": "error"}, warnings_result)
    assert len(brief["warnings"]) == 1
    assert "Warnings:" in morning_brief.format_brief_text(brief)
    # Without warnings the section stays out (FP104 behaviour unchanged).
    brief2 = morning_brief.build_morning_brief(now, [], {}, {}, {}, {"status": "error"})
    assert brief2["warnings"] == []
    assert "Warnings:" not in morning_brief.format_brief_text(brief2)


# --- route ---

def test_warnings_route_is_open():
    client = main.app.test_client()
    with patch.object(main, "get_warnings", return_value={"status": "not_configured"}):
        response = client.get("/api/weather/warnings")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is False
    assert body["status"] == "not_configured"


# --- template ---

def test_warnings_hooks_in_template():
    html = template_text()
    assert '<div id="weather-warnings"></div>' in html
    assert 'id="hub-warnings-card"' in html
    assert 'id="hub-warnings"' in html
    assert "Met Office Weather Warnings" in html
    assert "loadWeatherWarnings();" in function_body(html, "showWeather")
    assert "loadMorningHubWarnings();" in function_body(html, "renderMorningHub")
    assert "/api/weather/warnings" in function_body(html, "loadWeatherWarnings")
    assert "/api/weather/warnings" in function_body(html, "loadMorningHubWarnings")
    assert "warningBannerHtml" in function_body(html, "loadWeatherWarnings")


def test_warning_banner_html_renders_in_node():
    html = template_text()
    start = html.index("const WARNING_LEVEL_COLOURS")
    end = html.index("async function loadWeatherWarnings")
    block = html[start:end]
    escape_start = html.index("function escapeHtml(value)")
    escape_end = html.index("\n", escape_start)
    escape_fn = html[escape_start:escape_end]
    harness = (
        "const document = {createElement: () => ({set textContent(v) { this._t = v; }, get innerHTML() { "
        "return String(this._t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }})};\n"
        + escape_fn
        + "\n"
        + block
        + "\nconst out = warningBannerHtml({level: 'AMBER', types: ['RAIN', 'WIND'], headline: 'Heavy rain & <wind>', valid_from: '2026-11-16T10:00:00Z', valid_to: '2026-11-16T22:00:00Z'});\n"
        + "console.log(JSON.stringify({html: out, colour: warningLevelColour('RED'), unknown: warningLevelColour('PURPLE')}));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(harness)
        path = handle.name
    result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout.strip())
    assert "AMBER" in data["html"]
    assert "RAIN, WIND" in data["html"]
    assert "Heavy rain &amp; &lt;wind&gt;" in data["html"]
    assert "var(--orange)" in data["html"]
    assert data["colour"] == "var(--red)"
    assert data["unknown"] == "var(--amber)"
