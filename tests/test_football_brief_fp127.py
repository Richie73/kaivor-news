"""FP127: football in the morning brief — today's fixtures and last
night's results, from the FP110 ESPN scores feed.

The brief runs at 06:00, so fixtures are the day's games and
results are yesterday's finished games. Live games (rare at
06:00) list first with their clock. Anything the feed does not
carry just omits its lines — the section never breaks the brief.
"""
from datetime import datetime
from unittest.mock import patch

import main
from morning_brief import (
    LONDON,
    _london_match_time,
    brief_football_lines,
    build_morning_brief,
    format_brief_text,
)


def _match(home, away, date, state, home_score=None, away_score=None, clock=""):
    return {
        "id": f"{home}-{away}",
        "league": "eng.1",
        "home": home,
        "home_short": home,
        "home_score": home_score,
        "away": away,
        "away_short": away,
        "away_score": away_score,
        "state": state,
        "clock": clock,
        "detail": "",
        "date": date,
    }


def _scores(premier_league=(), england=(), status="ok"):
    return {
        "status": status,
        "updated": 0,
        "premier_league": list(premier_league),
        "england": list(england),
        "live_count": 0,
    }


def test_today_fixtures_listed_with_kickoff():
    scores = _scores(
        premier_league=[
            _match("Arsenal", "Chelsea", "2026-11-20T17:30Z", "pre"),
            _match("Spurs", "Newcastle", "2026-11-20T20:00Z", "pre"),
        ]
    )
    assert brief_football_lines(scores, "2026-11-20") == [
        "Today 17:30 \u2014 Arsenal v Chelsea",
        "Today 20:00 \u2014 Spurs v Newcastle",
    ]


def test_kickoff_converts_to_london_time():
    # Winter: GMT, so 17:30Z stays 17:30. Summer: BST, so 16:30Z is 17:30.
    winter = _scores(premier_league=[_match("Arsenal", "Chelsea", "2026-11-20T17:30Z", "pre")])
    assert brief_football_lines(winter, "2026-11-20") == ["Today 17:30 \u2014 Arsenal v Chelsea"]
    summer = _scores(premier_league=[_match("Arsenal", "Chelsea", "2026-07-04T16:30Z", "pre")])
    assert brief_football_lines(summer, "2026-07-04") == ["Today 17:30 \u2014 Arsenal v Chelsea"]


def test_yesterday_results_listed():
    scores = _scores(
        premier_league=[
            _match("Liverpool", "Man City", "2026-11-19T20:00Z", "post", 2, 1),
            _match("Brentford", "Brighton", "2026-11-19T19:45Z", "post", 0, 0),
        ]
    )
    assert brief_football_lines(scores, "2026-11-20") == [
        "Last night \u2014 Liverpool 2\u20131 Man City",
        "Last night \u2014 Brentford 0\u20130 Brighton",
    ]


def test_live_match_listed_first_with_clock():
    scores = _scores(
        premier_league=[
            _match("Arsenal", "Chelsea", "2026-11-20T17:30Z", "pre"),
            _match("Liverpool", "Man City", "2026-11-20T12:30Z", "in", 1, 0, "67'"),
        ]
    )
    assert brief_football_lines(scores, "2026-11-20") == [
        "Live 67' \u2014 Liverpool 1\u20130 Man City",
        "Today 17:30 \u2014 Arsenal v Chelsea",
    ]


def test_tomorrow_fixtures_and_old_results_excluded():
    scores = _scores(
        premier_league=[
            _match("Arsenal", "Chelsea", "2026-11-21T17:30Z", "pre"),
            _match("Liverpool", "Man City", "2026-11-18T20:00Z", "post", 2, 1),
        ]
    )
    assert brief_football_lines(scores, "2026-11-20") == []


def test_no_football_when_feed_unavailable():
    assert brief_football_lines(None, "2026-11-20") == []
    assert brief_football_lines(_scores(status="error"), "2026-11-20") == []
    assert brief_football_lines(_scores(), "2026-11-20") == []
    assert brief_football_lines("not a dict", "2026-11-20") == []


def test_football_lines_capped():
    fixtures = [
        _match(f"Home{i}", f"Away{i}", f"2026-11-20T1{i}:30Z", "pre") for i in range(6)
    ]
    results = [
        _match(f"Home{i}", f"Away{i}", "2026-11-19T20:00Z", "post", 1, 0)
        for i in range(5)
    ]
    lines = brief_football_lines(_scores(premier_league=fixtures + results), "2026-11-20")
    assert len([line for line in lines if line.startswith("Today")]) == 5
    assert len([line for line in lines if line.startswith("Last night")]) == 4


def test_unparseable_dates_and_missing_scores_skipped():
    scores = _scores(
        premier_league=[
            _match("Arsenal", "Chelsea", "not a date", "pre"),
            _match("Arsenal", "Chelsea", "", "pre"),
            _match("Liverpool", "Man City", "2026-11-19T20:00Z", "post"),
            _match("", "Man City", "2026-11-20T17:30Z", "pre"),
        ]
    )
    assert brief_football_lines(scores, "2026-11-20") == []


def test_england_matches_included():
    scores = _scores(
        england=[_match("England", "France", "2026-11-20T19:45Z", "pre")]
    )
    assert brief_football_lines(scores, "2026-11-20") == [
        "Today 19:45 \u2014 England v France"
    ]


def test_build_morning_brief_includes_football_section():
    scores = _scores(
        premier_league=[
            _match("Arsenal", "Chelsea", "2026-11-20T17:30Z", "pre"),
            _match("Liverpool", "Man City", "2026-11-19T20:00Z", "post", 2, 1),
        ]
    )
    now = datetime(2026, 11, 20, 6, 0, tzinfo=LONDON)
    brief = build_morning_brief(now, [], {}, {}, {}, {"status": "error"}, football=scores)
    assert brief["football"] == [
        "Today 17:30 \u2014 Arsenal v Chelsea",
        "Last night \u2014 Liverpool 2\u20131 Man City",
    ]
    text = format_brief_text(brief)
    assert "\nFootball:\n\u2022 Today 17:30 \u2014 Arsenal v Chelsea" in text
    assert "\u2022 Last night \u2014 Liverpool 2\u20131 Man City" in text


def test_build_morning_brief_without_football_has_no_section():
    now = datetime(2026, 11, 20, 6, 0, tzinfo=LONDON)
    brief = build_morning_brief(now, [], {}, {}, {}, {"status": "error"})
    assert brief["football"] == []
    assert "Football:" not in format_brief_text(brief)


def test_build_live_brief_passes_football():
    today = datetime.now(LONDON).date()
    fixture = _match("Arsenal", "Chelsea", f"{today.isoformat()}T12:00Z", "pre")
    scores = _scores(premier_league=[fixture])
    _, kickoff = _london_match_time(f"{today.isoformat()}T12:00Z")
    with (
        patch.object(main, "get_calendar", return_value={"status": "not_configured"}),
        patch.object(main, "get_travel", return_value={}),
        patch.object(main, "fetch_brief_weather", return_value={"status": "error"}),
        patch.object(main, "get_warnings", return_value={"status": "not_configured"}),
        patch.object(main, "task_store_or_none", return_value=None),
        patch.object(main, "get_scores", return_value=scores),
    ):
        brief = main._build_live_brief()
    assert brief["football"] == [f"Today {kickoff} \u2014 Arsenal v Chelsea"]


def test_build_live_brief_survives_scores_failure():
    with (
        patch.object(main, "get_calendar", return_value={"status": "not_configured"}),
        patch.object(main, "get_travel", return_value={}),
        patch.object(main, "fetch_brief_weather", return_value={"status": "error"}),
        patch.object(main, "get_warnings", return_value={"status": "not_configured"}),
        patch.object(main, "task_store_or_none", return_value=None),
        patch.object(main, "get_scores", side_effect=RuntimeError("ESPN down")),
    ):
        brief = main._build_live_brief()
    assert brief["football"] == []
