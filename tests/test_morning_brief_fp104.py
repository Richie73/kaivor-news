"""FP104: morning brief for phone automation (MacroDroid / Tasker).

One builder serves two delivery paths: GET /api/automation/brief
returns the brief as JSON for a Tasker pull, and POST
/api/automation/brief/send POSTs the plain-text brief to the
MacroDroid webhook URL. Both routes use the cron token, not the
Reading PIN — automation clients cannot hold a session cookie.
The text is capped at 3500 chars (MacroDroid's webhook body cap
is 3800). Also in this milestone: the National Highways
attribution line in the hub travel card, which their licence
asks for wherever closures data is shown.
"""
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests

import main
import morning_brief
from morning_brief import (
    MAX_BRIEF_CHARS,
    brief_calendar_lines,
    brief_greeting,
    brief_markets,
    brief_top_stories,
    brief_travel_lines,
    build_morning_brief,
    fetch_brief_weather,
    format_brief_text,
    send_brief_to_webhook,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

MONDAY_7AM = datetime(2026, 11, 16, 7, 0, tzinfo=morning_brief.LONDON)

SAMPLE_WEATHER = {
    "status": "ok",
    "place": "Puddington, Wirral",
    "temp": 7,
    "feels": 5,
    "condition": "Clear sky",
    "icon": "\u2600\ufe0f",
    "wind": 8,
    "high": 9,
    "low": 2,
    "rain_chance": 10,
}

SAMPLE_ARTICLES = [
    {"title": "First story", "source": "BBC"},
    {"title": "Second story", "source": "Guardian"},
    {"title": "", "source": "No title"},
    {"title": "Third story", "source": "Sky"},
    {"title": "Fourth story", "source": "BBC"},
    {"title": "Fifth story", "source": "Guardian"},
    {"title": "Sixth story", "source": "Sky"},
]

SAMPLE_FINANCE = {"Gold": 2650.0, "GBP_USD": 1.33524}

SAMPLE_CALENDAR = {
    "status": "ok",
    "events": [
        {"summary": "Site induction", "all_day": False, "start": "08:00", "end": "08:30"},
        {"summary": "Dentist", "all_day": False, "start": "09:15", "end": None},
        {"summary": "Bank holiday", "all_day": True, "start": None, "end": None},
    ],
}

SAMPLE_TRAVEL_GOOD = {
    "rail": {"status": "ok", "disruptions": []},
    "national_highways": {"status": "ok", "closures": []},
    "tomtom": {"status": "ok", "incidents": []},
    "tunnels": {"link": "https://www.merseytravel.gov.uk/travel-updates/", "incidents": []},
}

SAMPLE_TRAVEL_BUSY = {
    "rail": {
        "status": "ok",
        "disruptions": [{"summary": "Delays between Rock Ferry and Hooton", "severity": "severe"}],
    },
    "national_highways": {
        "status": "ok",
        "closures": [{"road": "M53", "description": "Lane closed J5-J6"}],
    },
    "tomtom": {
        "status": "ok",
        "incidents": [{"road": "A41", "description": "Slow traffic", "delay_minutes": 12, "tunnel": False}],
    },
    "tunnels": {
        "link": "https://www.merseytravel.gov.uk/travel-updates/",
        "incidents": [{"description": "Queuing at the Kingsway Tunnel", "tunnel": True}],
    },
}


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, name):
    match = re.search(rf"function {name}\(.*?\n\}}", html, re.S)
    assert match, f"{name} missing"
    return match.group(0)


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self._payload


# --- greeting ---

def test_brief_greeting_bands():
    assert brief_greeting(4) == "Good night"
    assert brief_greeting(5) == "Good morning"
    assert brief_greeting(11) == "Good morning"
    assert brief_greeting(12) == "Good afternoon"
    assert brief_greeting(17) == "Good afternoon"
    assert brief_greeting(18) == "Good evening"
    assert brief_greeting(22) == "Good evening"
    assert brief_greeting(23) == "Good night"


# --- builder ---

def test_build_morning_brief_assembles_sections():
    brief = build_morning_brief(
        MONDAY_7AM, SAMPLE_ARTICLES, SAMPLE_FINANCE, SAMPLE_CALENDAR,
        SAMPLE_TRAVEL_GOOD, SAMPLE_WEATHER,
    )
    assert brief["greeting"] == "Good morning, Richie"
    assert brief["date"] == "2026-11-16"
    assert brief["date_text"] == "Monday 16 November 2026"
    assert brief["weather"]["condition"] == "Clear sky"
    assert [s["title"] for s in brief["stories"]] == [
        "First story", "Second story", "Third story", "Fourth story", "Fifth story",
    ]
    assert brief["markets"] == [
        {"label": "Gold", "value": "$2,650.00"},
        {"label": "\u00a3 \u2192 $", "value": "1.3352"},
    ]
    assert brief["calendar"] == [
        "08:00\u201308:30 Site induction",
        "09:15 Dentist",
        "All day \u2014 Bank holiday",
    ]
    assert brief["travel"] == [
        "\U0001f686 Wirral Line \u2014 Good service",
        "\U0001f6e3\ufe0f M53 \u00b7 M56 \u00b7 A41 \u2014 No incidents",
    ]


def test_build_morning_brief_empty_inputs():
    brief = build_morning_brief(
        MONDAY_7AM, [], {}, {"status": "error"}, {"rail": {"status": "not_configured"}},
        {"status": "error", "error": "Weather unavailable."},
    )
    assert brief["stories"] == []
    assert brief["markets"] == []
    assert brief["calendar"] == []
    assert brief["travel"] == []
    assert brief["weather"]["status"] == "error"


def test_brief_top_stories_skips_untitled_and_caps():
    stories = brief_top_stories(SAMPLE_ARTICLES)
    assert len(stories) == 5
    assert all(s["title"] for s in stories)
    assert stories[0] == {"title": "First story", "source": "BBC"}


def test_brief_markets_formats_values():
    assert brief_markets({"Gold": 2650.0, "Bitcoin": 87432.1, "GBP_USD": 1.33524}) == [
        {"label": "Gold", "value": "$2,650.00"},
        {"label": "Bitcoin", "value": "$87,432.10"},
        {"label": "\u00a3 \u2192 $", "value": "1.3352"},
    ]
    assert brief_markets({}) == []
    assert brief_markets({"Gold": "not a number"}) == []


def test_brief_travel_lines_with_disruption_and_closure():
    lines = brief_travel_lines(SAMPLE_TRAVEL_BUSY)
    assert lines[0] == "\U0001f686 Delays between Rock Ferry and Hooton \u2014 severe"
    assert "\U0001f6e3\ufe0f M53: Lane closed J5-J6" in lines
    assert "\U0001f6e3\ufe0f A41: Slow traffic (delay ~12 min)" in lines
    assert "\U0001f687 Tunnel: Queuing at the Kingsway Tunnel" in lines


def test_format_brief_text_contains_sections():
    brief = build_morning_brief(
        MONDAY_7AM, SAMPLE_ARTICLES, SAMPLE_FINANCE, SAMPLE_CALENDAR,
        SAMPLE_TRAVEL_GOOD, SAMPLE_WEATHER,
    )
    text = format_brief_text(brief)
    assert text.startswith("Good morning, Richie \u2014 Monday 16 November 2026")
    assert "Puddington, Wirral: 7\u00b0 Clear sky" in text
    assert "Top stories:" in text and "First story (BBC)" in text
    assert "Markets: Gold $2,650.00, \u00a3 \u2192 $ 1.3352" in text
    assert "08:00\u201308:30 Site induction" in text
    assert "Wirral Line \u2014 Good service" in text
    assert len(text) <= MAX_BRIEF_CHARS


def test_format_brief_text_caps_length():
    brief = {
        "greeting": "Good morning, Richie",
        "date_text": "Monday 16 November 2026",
        "weather": SAMPLE_WEATHER,
        "stories": [],
        "markets": [],
        "calendar": [f"Event number {n} " + ("x" * 100) for n in range(100)],
        "travel": [],
    }
    text = format_brief_text(brief)
    assert len(text) == MAX_BRIEF_CHARS
    assert text.endswith("\u2026")


# --- weather fetch ---

def test_fetch_brief_weather_parses_response():
    payload = {
        "current": {
            "temperature_2m": 7.2,
            "apparent_temperature": 5.1,
            "weather_code": 0,
            "wind_speed_10m": 8.4,
        },
        "daily": {
            "temperature_2m_max": [9.4],
            "temperature_2m_min": [2.1],
            "precipitation_probability_max": [10],
        },
    }
    with patch.object(morning_brief.requests, "get", return_value=FakeResponse(payload)) as get:
        result = fetch_brief_weather()
    assert result["status"] == "ok"
    assert result["temp"] == 7
    assert result["feels"] == 5
    assert result["condition"] == "Clear sky"
    assert result["high"] == 9
    assert result["low"] == 2
    assert result["rain_chance"] == 10
    assert result["wind"] == 8
    params = get.call_args.kwargs["params"]
    assert params["latitude"] == 53.25332
    assert params["timezone"] == "Europe/London"


def test_fetch_brief_weather_failure():
    with patch.object(
        morning_brief.requests, "get", return_value=FakeResponse({}, status_code=500)
    ):
        assert fetch_brief_weather()["status"] == "error"
    with patch.object(
        morning_brief.requests, "get", side_effect=requests.RequestException("down")
    ):
        assert fetch_brief_weather()["status"] == "error"


# --- webhook send ---

def test_send_brief_to_webhook_posts_text():
    with patch.object(
        morning_brief.requests, "post", return_value=FakeResponse({}, status_code=200)
    ) as post:
        result = send_brief_to_webhook("https://trigger.macrodroid.com/abc/def", "Hello")
    assert result == {"ok": True, "status": 200}
    post.assert_called_once()
    assert post.call_args.args[0] == "https://trigger.macrodroid.com/abc/def"
    assert post.call_args.kwargs["data"] == b"Hello"
    assert "text/plain" in post.call_args.kwargs["headers"]["Content-Type"]


def test_send_brief_to_webhook_rejects_bad_url_and_failure():
    assert send_brief_to_webhook("", "Hello")["ok"] is False
    assert send_brief_to_webhook("http://trigger.macrodroid.com/abc", "Hello")["ok"] is False
    with patch.object(
        morning_brief.requests, "post", return_value=FakeResponse({}, status_code=403)
    ):
        result = send_brief_to_webhook("https://trigger.macrodroid.com/abc/def", "Hello")
    assert result["ok"] is False
    assert "403" in result["error"]
    with patch.object(
        morning_brief.requests, "post", side_effect=requests.RequestException("down")
    ):
        assert send_brief_to_webhook("https://trigger.macrodroid.com/abc/def", "Hello")["ok"] is False


# --- routes ---

def test_brief_route_requires_cron_token():
    client = main.app.test_client()
    with patch.dict(main.os.environ, {"KAIVOR_CRON_TOKEN": "fp104-test-token"}, clear=False):
        response = client.get("/api/automation/brief")
        assert response.status_code == 401
        response = client.get(
            "/api/automation/brief", headers={"Authorization": "Bearer wrong"}
        )
        assert response.status_code == 401
        sample = build_morning_brief(
            MONDAY_7AM, SAMPLE_ARTICLES, SAMPLE_FINANCE, SAMPLE_CALENDAR,
            SAMPLE_TRAVEL_GOOD, SAMPLE_WEATHER,
        )
        with patch.object(main, "_build_live_brief", return_value=sample):
            response = client.get(
                "/api/automation/brief",
                headers={"Authorization": "Bearer fp104-test-token"},
            )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["brief"]["greeting"] == "Good morning, Richie"
    assert "Good morning, Richie" in body["text"]


def test_send_route_requires_token_and_webhook_url():
    client = main.app.test_client()
    with patch.dict(main.os.environ, {"KAIVOR_CRON_TOKEN": "fp104-test-token"}, clear=False):
        with patch.dict(main.os.environ, {}, clear=False):
            main.os.environ.pop("KAIVOR_MACRODROID_WEBHOOK_URL", None)
            response = client.post(
                "/api/automation/brief/send",
                headers={"Authorization": "Bearer fp104-test-token"},
            )
            assert response.status_code == 503
        response = client.post("/api/automation/brief/send")
        assert response.status_code == 401
        sample = build_morning_brief(
            MONDAY_7AM, SAMPLE_ARTICLES, SAMPLE_FINANCE, SAMPLE_CALENDAR,
            SAMPLE_TRAVEL_GOOD, SAMPLE_WEATHER,
        )
        with patch.dict(
            main.os.environ,
            {"KAIVOR_MACRODROID_WEBHOOK_URL": "https://trigger.macrodroid.com/abc/def"},
            clear=False,
        ):
            with (
                patch.object(main, "_build_live_brief", return_value=sample),
                patch.object(main, "send_brief_to_webhook", return_value={"ok": True, "status": 200}) as send,
            ):
                response = client.post(
                    "/api/automation/brief/send",
                    headers={"Authorization": "Bearer fp104-test-token"},
                )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["delivered"] is True
    assert body["chars"] > 0
    send.assert_called_once()
    assert send.call_args.args[0] == "https://trigger.macrodroid.com/abc/def"


# --- template: National Highways attribution ---

def test_nh_attribution_in_travel_loader():
    travel_body = function_body(template_text(), "loadMorningHubTravel")
    assert "Powered by National Highways\\' Transport Data Feeds" in travel_body
    assert "nh.status !== 'not_configured'" in travel_body
