"""FP103: morning hub v2 — today's calendar + live Wirral travel.

Calendar comes from the user's Google Calendar secret iCal feed
(server-side fetch, 30-minute cache, recurrences expanded); the
route is PIN-gated because the data is private. Travel is public
data on an open route: Merseyrail disruption (TransCAPI),
M53/M56 closures (National Highways DATEX II v2.0) and A41 +
tunnel approaches (TomTom Traffic Incidents). No public API
exists for the tunnels themselves — the hub links to
Merseytravel's live page. Every source is independently
optional: a missing key reports "not_configured".
"""
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import main
import hub_services
from hub_services import (
    fetch_calendar,
    fetch_rail,
    fetch_travel,
    get_calendar,
    parse_ics_events,
    parse_nh_closures,
    parse_tomtom_incidents,
    parse_transcapi_disruptions,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:oneoff@test
DTSTAMP:20261115T000000Z
DTSTART:20261116T091500Z
DTEND:20261116T100000Z
SUMMARY:Dentist appointment
END:VEVENT
BEGIN:VEVENT
UID:daily@test
DTSTAMP:20261115T000000Z
DTSTART:20261110T070000Z
DTEND:20261110T073000Z
RRULE:FREQ=DAILY
SUMMARY:Morning walk
END:VEVENT
BEGIN:VEVENT
UID:allday@test
DTSTAMP:20261115T000000Z
DTSTART;VALUE=DATE:20261116
DTEND;VALUE=DATE:20261117
SUMMARY:Site shutdown day
END:VEVENT
BEGIN:VEVENT
UID:nosummary@test
DTSTAMP:20261115T000000Z
DTSTART:20261116T120000Z
DTEND:20261116T123000Z
END:VEVENT
END:VCALENDAR
"""

TRANSCAPI_SAMPLE = {
    "member": [
        {
            "id": "NRE-1", "source": "nre_kb", "modes": ["rail"], "severity": "minor",
            "planned": False, "summary": "Delays on the Northern Line",
            "description": "Trains may be delayed by up to 10 minutes.",
            "advice": "", "lines": [{"line": "Northern Line"}],
            "stops_count": 0, "url": None,
        },
        {
            "id": "NRE-2", "source": "nre_kb", "modes": ["rail"], "severity": "severe",
            "planned": False, "summary": "No trains between Bidston and Liverpool",
            "description": "Buses replace trains due to a points failure.",
            "advice": "Allow extra time.", "lines": [{"line": "Wirral Line"}],
            "stops_count": 0, "url": "https://example.com/nre-2",
        },
    ]
}

NH_SAMPLE = {
    "D2Payload": {
        "situation": [
            {"situationRecord": [
                {
                    "validity": {"validityTimeSpecification": {
                        "overallStartTime": "2026-11-15T08:00:00Z",
                        "overallEndTime": "2026-11-20T18:00:00Z"}},
                    "generalPublicComment": [{"comment": "Lane 1 closed for resurfacing"}],
                    "locationReference": {"locLinearLocation": {"locSingleRoadLinearLocation": {"locLinearElementByCode": {"roadName": "M53"}}}},
                },
                {
                    "validity": {"validityTimeSpecification": {
                        "overallStartTime": "2026-11-15T08:00:00Z",
                        "overallEndTime": "2026-11-20T18:00:00Z"}},
                    "generalPublicComment": [{"comment": "Lane 1 closed for resurfacing"}],
                    "locationReference": {"locLinearLocation": {"locSingleRoadLinearLocation": {"locLinearElementByCode": {"roadName": "M53"}}}},
                },
                {
                    "validity": {"validityTimeSpecification": {
                        "overallStartTime": "2026-11-01T08:00:00Z",
                        "overallEndTime": "2026-11-02T18:00:00Z"}},
                    "generalPublicComment": [{"comment": "Old M56 works"}],
                    "locationReference": {"locLinearLocation": {"locSingleRoadLinearLocation": {"locLinearElementByCode": {"roadName": "M56"}}}},
                },
                {
                    "validity": {"validityTimeSpecification": {
                        "overallStartTime": "2026-11-15T08:00:00Z",
                        "overallEndTime": "2026-11-20T18:00:00Z"}},
                    "generalPublicComment": [{"comment": "M6 works"}],
                    "locationReference": {"locLinearLocation": {"locSingleRoadLinearLocation": {"locLinearElementByCode": {"roadName": "M6"}}}},
                },
            ]}
        ]
    }
}

TOMTOM_SAMPLE = {
    "incidents": [
        {
            "properties": {
                "roadNumbers": ["A41"],
                "events": [{"description": "Roadworks on A41 near Backford"}],
                "from": "Backford", "to": "Chester", "delay": 600,
            }
        },
        {
            "properties": {
                "roadNumbers": [],
                "events": [{"description": "Kingsway Tunnel closed northbound"}],
                "from": "Wallasey", "to": "Liverpool", "delay": 1200,
            }
        },
        {
            "properties": {
                "roadNumbers": ["M53"],
                "events": [{"description": "Slow traffic on M53"}],
                "from": "J4", "to": "J5", "delay": 300,
            }
        },
    ]
}


class FakeTextResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(rf"function {name}\(.*?\n\}}", html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


# --- calendar ---

def test_parse_ics_events_expands_recurrences():
    events = parse_ics_events(SAMPLE_ICS, day=date(2026, 11, 16))
    assert len(events) == 3  # the event without a summary is skipped
    by_summary = {event["summary"]: event for event in events}
    assert by_summary["Dentist appointment"]["start"] == "09:15"
    assert by_summary["Dentist appointment"]["end"] == "10:00"
    assert by_summary["Dentist appointment"]["all_day"] is False
    assert by_summary["Morning walk"]["start"] == "07:00"  # recurring daily event
    assert by_summary["Site shutdown day"]["all_day"] is True
    assert by_summary["Site shutdown day"]["start"] is None


def test_fetch_calendar_not_configured():
    assert fetch_calendar(None) == {"status": "not_configured"}
    assert fetch_calendar("") == {"status": "not_configured"}


def test_calendar_result_is_cached(monkeypatch):
    monkeypatch.setattr(hub_services, "_calendar_cache", {"data": None, "fetched": 0})
    with patch.object(hub_services.requests, "get", return_value=FakeTextResponse(200, SAMPLE_ICS)) as getter:
        first = get_calendar("https://example.com/feed.ics", day=date(2026, 11, 16))
        second = get_calendar("https://example.com/feed.ics", day=date(2026, 11, 16))
    assert getter.call_count == 1
    assert first == second
    assert first["status"] == "ok"
    assert len(first["events"]) == 3


# --- rail ---

def test_parse_transcapi_disruptions_wirral_first():
    disruptions = parse_transcapi_disruptions(TRANSCAPI_SAMPLE)
    assert len(disruptions) == 2
    assert disruptions[0]["severity"] == "severe"
    assert disruptions[0]["lines"] == ["Wirral Line"]
    assert disruptions[0]["summary"] == "No trains between Bidston and Liverpool"
    assert disruptions[1]["lines"] == ["Northern Line"]


def test_fetch_rail_not_configured():
    assert fetch_rail(None) == {"status": "not_configured"}


# --- roads ---

def test_parse_nh_closures_filters_road_time_and_duplicates():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime(2026, 11, 16, 12, 0, tzinfo=ZoneInfo("Europe/London"))
    closures = parse_nh_closures(NH_SAMPLE, now=now)
    assert len(closures) == 1  # M53 kept; M56 expired, M6 wrong road, duplicate dropped
    assert closures[0]["road"] == "M53"
    assert "resurfacing" in closures[0]["description"]


def test_parse_tomtom_incidents_a41_and_tunnels_only():
    incidents = parse_tomtom_incidents(TOMTOM_SAMPLE)
    assert len(incidents) == 2  # the M53 incident is not A41 or tunnel
    assert incidents[0]["road"] == "A41"
    assert incidents[0]["delay_minutes"] == 10
    assert incidents[0]["tunnel"] is False
    assert incidents[1]["tunnel"] is True
    assert incidents[1]["delay_minutes"] == 20


def test_fetch_travel_combines_sources():
    rail = {"status": "ok", "disruptions": []}
    nh = {"status": "ok", "closures": []}
    tomtom = {"status": "ok", "incidents": parse_tomtom_incidents(TOMTOM_SAMPLE)}
    with patch.object(hub_services, "fetch_rail", return_value=rail), \
            patch.object(hub_services, "fetch_nh_closures", return_value=nh), \
            patch.object(hub_services, "fetch_tomtom", return_value=tomtom):
        result = fetch_travel("rail-key", "nh-key", "tomtom-key")
    assert result["rail"] == rail
    assert result["national_highways"] == nh
    assert result["tomtom"] == tomtom
    assert result["tunnels"]["link"] == "https://www.merseytravel.gov.uk/travel-updates/"
    assert len(result["tunnels"]["incidents"]) == 1
    assert result["tunnels"]["incidents"][0]["tunnel"] is True


# --- routes ---

def test_hub_calendar_route_is_pin_gated(authed_client):
    client = main.app.test_client()
    response = client.get("/api/hub/calendar")
    assert response.status_code in {401, 503}
    with patch.object(main, "get_calendar", return_value={"status": "ok", "events": []}):
        response = authed_client.get("/api/hub/calendar")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_hub_travel_route_is_open():
    client = main.app.test_client()
    with patch.object(main, "get_travel", return_value={"rail": {"status": "not_configured"}, "national_highways": {"status": "not_configured"}, "tomtom": {"status": "not_configured"}, "tunnels": {"link": "https://www.merseytravel.gov.uk/travel-updates/", "incidents": []}}):
        response = client.get("/api/hub/travel")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


# --- template ---

def test_hub_calendar_and_travel_cards():
    html = template_text()
    assert '<div id="hub-calendar" class="hub-list">' in html
    assert '<div id="hub-travel" class="hub-list">' in html
    assert "loadMorningHubCalendar();" in function_body(html, "renderMorningHub")
    assert "loadMorningHubTravel();" in function_body(html, "renderMorningHub")
    calendar_body = function_body(html, "loadMorningHubCalendar")
    assert "/api/hub/calendar" in calendar_body
    assert "Unlock Reading to see today\\'s calendar." in calendar_body
    travel_body = function_body(html, "loadMorningHubTravel")
    assert "/api/hub/travel" in travel_body
    assert "Good service" in travel_body
    assert "merseytravel.gov.uk/travel-updates" in travel_body
