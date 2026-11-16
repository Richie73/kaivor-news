"""FP110: live football scores (Premier League + England) from ESPN's free
scoreboard feed.

No API key, no signup: https://site.api.espn.com/apis/site/v2/sports/soccer/
{league}/scoreboard returns the current gameweek's fixtures with live
scores, the match clock and results. The feed is unofficial and updates
roughly every 30-60 seconds during play, so scores are near-live, not
truly instant (see CHANGELOG_FP110.txt).

England play across several competitions (friendlies, Nations League,
World Cup qualifiers, Euro qualifiers, World Cup, Euros), so their games
are picked out of those scoreboards by team name; there is nothing to
show between international windows.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
)
PREMIER_LEAGUE = "eng.1"
# Competitions England can appear in. Each scoreboard is fetched in
# parallel; leagues that fail just contribute nothing.
ENGLAND_LEAGUES = (
    "fifa.friendly",
    "uefa.nations",
    "fifa.worldq.uefa",
    "uefa.euroq",
    "fifa.world",
    "uefa.euro",
)
ENGLAND_TEAM_NAME = "England"

# 30 seconds: the client polls every 30s while the Sport view is open,
# and ESPN's own data moves on a similar cadence.
SCORES_TTL = 30
_FETCH_TIMEOUT_SECONDS = 10
_MAX_MATCHES_PER_LIST = 20

_SCORES_CACHE = {"data": None, "fetched_at": 0}


def _competitor(competitors: list[dict[str, Any]], home_away: str) -> dict[str, Any]:
    for competitor in competitors:
        if competitor.get("homeAway") == home_away:
            return competitor
    return competitors[0] if competitors else {}


def _score_value(competitor: dict[str, Any]) -> int | None:
    raw = competitor.get("score")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def parse_scoreboard(payload: dict[str, Any], league: str) -> list[dict[str, Any]]:
    """Map one ESPN scoreboard payload to Kaivor match dicts."""
    matches: list[dict[str, Any]] = []
    for event in payload.get("events") or []:
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        competition = competitions[0]
        competitors = competition.get("competitors") or []
        if len(competitors) < 2:
            continue
        home = _competitor(competitors, "home")
        away = _competitor(competitors, "away")
        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        status = event.get("status") or {}
        state = (status.get("type") or {}).get("state") or "pre"
        matches.append(
            {
                "id": str(event.get("id") or competition.get("id") or ""),
                "league": league,
                "home": str(home_team.get("displayName") or ""),
                "home_short": str(home_team.get("shortDisplayName") or home_team.get("displayName") or ""),
                "home_score": _score_value(home),
                "away": str(away_team.get("displayName") or ""),
                "away_short": str(away_team.get("shortDisplayName") or away_team.get("displayName") or ""),
                "away_score": _score_value(away),
                "state": state if state in {"pre", "in", "post"} else "pre",
                "clock": str(status.get("displayClock") or ""),
                "detail": str((status.get("type") or {}).get("detail") or ""),
                "date": str(event.get("date") or competition.get("date") or ""),
            }
        )
    return matches


def _sort_key(match: dict[str, Any]) -> tuple[int, str]:
    # Live games first, then scheduled by kickoff, then finished.
    group = {"in": 0, "pre": 1, "post": 2}.get(match.get("state"), 1)
    return (group, match.get("date") or "")


def fetch_league_scores(league: str) -> list[dict[str, Any]]:
    """Fetch and parse one league's scoreboard. Raises on failure."""
    response = requests.get(
        ESPN_SCOREBOARD_URL.format(league=league),
        headers={"User-Agent": "Kaivor-News/FP110"},
        timeout=_FETCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_scoreboard(response.json(), league)


def fetch_all_scores() -> dict[str, Any]:
    """Fetch the Premier League plus every England competition in parallel."""
    leagues = [PREMIER_LEAGUE, *ENGLAND_LEAGUES]
    premier_league: list[dict[str, Any]] = []
    england: list[dict[str, Any]] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_league_scores, league): league for league in leagues}
        for future in as_completed(futures):
            league = futures[future]
            try:
                matches = future.result()
            except Exception:
                failures += 1
                continue
            if league == PREMIER_LEAGUE:
                premier_league.extend(matches)
            else:
                england.extend(
                    match
                    for match in matches
                    if match["home"] == ENGLAND_TEAM_NAME or match["away"] == ENGLAND_TEAM_NAME
                )
    if failures == len(leagues):
        return {
            "status": "error",
            "error": "The scores feed could not be reached.",
            "updated": int(time.time()),
            "premier_league": [],
            "england": [],
            "live_count": 0,
        }
    premier_league.sort(key=_sort_key)
    england.sort(key=_sort_key)
    all_matches = premier_league + england
    return {
        "status": "ok",
        "updated": int(time.time()),
        "premier_league": premier_league[:_MAX_MATCHES_PER_LIST],
        "england": england[:_MAX_MATCHES_PER_LIST],
        "live_count": sum(1 for match in all_matches if match["state"] == "in"),
    }


def get_scores() -> dict[str, Any]:
    """Cached fetch (30s). Errors are cached too, like travel/warnings."""
    now = time.time()
    if _SCORES_CACHE["data"] is not None and now - _SCORES_CACHE["fetched_at"] < SCORES_TTL:
        return _SCORES_CACHE["data"]
    result = fetch_all_scores()
    _SCORES_CACHE["data"] = result
    _SCORES_CACHE["fetched_at"] = now
    return result
