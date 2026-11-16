"""FP110: live football scores (Premier League + England) in the Sport view.

Scores come from ESPN's free scoreboard feed (no key): the Premier League
scoreboard in full, plus England matches picked out of the international
competition scoreboards. The server caches for 30 seconds; the page
re-polls every 30 seconds while the Sport view is open.
"""
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import football_scores
import main
from football_scores import fetch_all_scores, get_scores, parse_scoreboard

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def _event(event_id, home, away, state, clock="", detail="",
           date="2026-11-21T15:00Z", home_score=None, away_score=None):
    return {
        "id": event_id,
        "date": date,
        "status": {"type": {"state": state, "detail": detail}, "displayClock": clock},
        "competitions": [{
            "id": event_id,
            "competitors": [
                {"homeAway": "home",
                 "team": {"displayName": home, "shortDisplayName": home[:3]},
                 "score": home_score},
                {"homeAway": "away",
                 "team": {"displayName": away, "shortDisplayName": away[:3]},
                 "score": away_score},
            ],
        }],
    }


def _payload(*events):
    return {"events": list(events)}


# --- parsing ---

def test_parse_scheduled_event():
    matches = parse_scoreboard(
        _payload(_event("1", "Man City", "Fulham", "pre")), "eng.1")
    assert matches == [{
        "id": "1", "league": "eng.1",
        "home": "Man City", "home_short": "Man", "home_score": None,
        "away": "Fulham", "away_short": "Ful", "away_score": None,
        "state": "pre", "clock": "", "detail": "",
        "date": "2026-11-21T15:00Z",
    }]


def test_parse_live_event_converts_scores_to_int():
    matches = parse_scoreboard(
        _payload(_event("2", "Arsenal", "Liverpool", "in", clock="67'",
                        home_score="2", away_score="1")),
        "eng.1")
    assert matches[0]["state"] == "in"
    assert matches[0]["clock"] == "67'"
    assert matches[0]["home_score"] == 2
    assert matches[0]["away_score"] == 1


def test_parse_finished_event_keeps_detail():
    matches = parse_scoreboard(
        _payload(_event("3", "Chelsea", "Spurs", "post", detail="Full Time",
                        home_score="3", away_score="0")),
        "eng.1")
    assert matches[0]["state"] == "post"
    assert matches[0]["detail"] == "Full Time"


def test_parse_skips_events_without_two_competitors():
    payload = {"events": [{"id": "9", "date": "2026-11-21T15:00Z",
                           "status": {"type": {"state": "pre"}},
                           "competitions": [{"competitors": []}]}]}
    assert parse_scoreboard(payload, "eng.1") == []


# --- aggregation ---

def _fake_fetch(league):
    if league == "eng.1":
        return parse_scoreboard(_payload(
            _event("1", "Man City", "Fulham", "pre"),
            _event("2", "Arsenal", "Liverpool", "in", clock="67'",
                   home_score="2", away_score="1"),
            _event("3", "Chelsea", "Spurs", "post", detail="Full Time",
                   home_score="3", away_score="0"),
        ), league)
    if league == "uefa.nations":
        return parse_scoreboard(_payload(
            _event("4", "England", "Spain", "pre", date="2026-11-22T19:45Z"),
            _event("5", "France", "Italy", "pre", date="2026-11-22T19:45Z"),
        ), league)
    return []


def test_england_filter_keeps_only_england_matches(monkeypatch):
    monkeypatch.setattr(football_scores, "fetch_league_scores", _fake_fetch)
    result = fetch_all_scores()
    assert result["status"] == "ok"
    assert [m["id"] for m in result["england"]] == ["4"]
    assert [m["id"] for m in result["premier_league"]] == ["2", "1", "3"]


def test_live_count_counts_live_matches(monkeypatch):
    monkeypatch.setattr(football_scores, "fetch_league_scores", _fake_fetch)
    assert fetch_all_scores()["live_count"] == 1


def test_one_league_failure_does_not_break_others(monkeypatch):
    def flaky(league):
        if league == "uefa.nations":
            raise RuntimeError("boom")
        return _fake_fetch(league)
    monkeypatch.setattr(football_scores, "fetch_league_scores", flaky)
    result = fetch_all_scores()
    assert result["status"] == "ok"
    assert len(result["premier_league"]) == 3
    assert result["england"] == []


def test_all_leagues_failing_returns_error(monkeypatch):
    monkeypatch.setattr(
        football_scores, "fetch_league_scores",
        lambda league: (_ for _ in ()).throw(RuntimeError("boom")))
    result = fetch_all_scores()
    assert result["status"] == "error"
    assert result["premier_league"] == []
    assert result["england"] == []


# --- caching ---

def test_cache_within_ttl_fetches_once(monkeypatch):
    monkeypatch.setattr(
        football_scores, "_SCORES_CACHE", {"data": None, "fetched_at": 0})
    calls = []
    monkeypatch.setattr(
        football_scores, "fetch_all_scores",
        lambda: calls.append(1) or {"status": "ok"})
    assert get_scores() == {"status": "ok"}
    assert get_scores() == {"status": "ok"}
    assert len(calls) == 1


def test_cache_refetches_after_ttl(monkeypatch):
    monkeypatch.setattr(
        football_scores, "_SCORES_CACHE",
        {"data": {"status": "ok"}, "fetched_at": time.time() - 31})
    calls = []
    monkeypatch.setattr(
        football_scores, "fetch_all_scores",
        lambda: calls.append(1) or {"status": "ok", "fresh": True})
    assert get_scores() == {"status": "ok", "fresh": True}
    assert len(calls) == 1


# --- route ---

def test_scores_route_is_open():
    client = main.app.test_client()
    payload = {"status": "ok", "updated": 0, "premier_league": [],
               "england": [], "live_count": 0}
    with patch.object(main, "get_scores", return_value=payload):
        response = client.get("/api/football/scores")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["status"] == "ok"


# --- template ---

def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_scores_strip_present_but_hidden():
    html = template_text()
    assert '<div id="football-scores" class="card" style="display:none"></div>' in html


def test_filter_category_hooks_scores():
    html = template_text()
    assert "updateFootballScores(category);" in html


def test_hide_calls_in_view_openers():
    html = template_text()
    assert "if (newsViewReplaced) return;\n    hideFootballScores();\n    hideNewsLoadMore();" in html
    assert "hideMarketsView();\n    hideMorningHubView();\n    hideFootballScores();" in html
    assert "function showMarkets() {\n    hideWeatherView();\n    hideMorningHubView();\n    hideFootballScores();" in html
    assert "function showMorningHub(element) {\n    hideWeatherView();\n    hideMarketsView();\n    hideFootballScores();" in html


def test_poll_interval_and_watch_link():
    html = template_text()
    assert "FOOTBALL_SCORES_POLL_MS = 30000" in html
    assert "setInterval(loadFootballScores, FOOTBALL_SCORES_POLL_MS)" in html
    assert "https://www.live-footballontv.com/" in html
    assert "Where to watch on UK TV" in html


def test_scores_css_uses_tokens():
    html = template_text()
    assert ".score-live { color:var(--red); font-weight:700; }" in html
    assert ".score-row { display:flex;" in html


# --- node: row rendering ---

NODE_PREAMBLE = """
const document = { createElement: () => { let raw = ''; return {
    set textContent(v) { raw = String(v ?? ''); },
    get innerHTML() { return raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
}; } };
"""

NODE_ASSERTIONS = """
const live = footballScoreRowHtml({home_short: 'ARS', away_short: 'LIV', state: 'in', clock: "67'", home_score: 2, away_score: 1, date: ''});
assert.ok(live.includes('LIVE'));
assert.ok(live.includes("67'"));
assert.ok(live.includes('2\\u20131'));
assert.ok(live.includes('ARS v LIV'));
const finished = footballScoreRowHtml({home_short: 'CHE', away_short: 'TOT', state: 'post', clock: '', home_score: 3, away_score: 0, date: ''});
assert.ok(finished.includes('FT 3\\u20130'));
const scheduled = footballScoreRowHtml({home_short: 'MCI', away_short: 'FUL', state: 'pre', clock: '', home_score: null, away_score: null, date: '2026-11-21T15:00:00Z'});
assert.ok(scheduled.includes('MCI v FUL'));
assert.ok(/\\d{2}:\\d{2}/.test(scheduled));
"""


def test_score_row_rendering_runs_under_node():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    html = template_text()
    row = re.search(
        r"function footballScoreRowHtml\(match\) \{(.*?)\n\}", html, re.S)
    assert row, "footballScoreRowHtml function missing"
    kickoff = re.search(
        r"function footballKickoffTime\(isoDate\) \{(.*?)\n\}", html, re.S)
    assert kickoff, "footballKickoffTime function missing"
    escape = re.search(r"function escapeHtml\(value\) \{[^\n]*\}", html)
    assert escape, "escapeHtml function missing"
    script = (
        "import assert from 'node:assert/strict';\n"
        + NODE_PREAMBLE
        + escape.group(0)
        + "\n"
        + kickoff.group(0)
        + "\n"
        + row.group(0)
        + NODE_ASSERTIONS
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        path = handle.name
    result = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
