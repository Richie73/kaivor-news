"""Morning hub live data (FP103): today's calendar + Wirral travel.

Calendar: the user's Google Calendar secret iCal feed
(KAIVOR_CALENDAR_ICS_URL — set by him in Render, never in chat),
fetched server-side and cached 30 minutes. Recurring events are
expanded, so a regular commitment shows on the day.

Travel (all server-side, cached 15 minutes):
- Merseyrail disruption via TransCAPI (TRANSCAPI_API_KEY).
- M53/M56 closures via National Highways DATEX II v2.0
  (NATIONAL_HIGHWAYS_API_KEY) — planned AND unplanned.
- A41 + tunnel approaches via TomTom Traffic Incidents
  (TOMTOM_API_KEY). No public API exists for the Mersey
  tunnels themselves, so the hub links to Merseytravel's
  live travel-updates page for per-tunnel journey times.

Every source is independently optional: a missing key means
that section reports "not_configured" instead of failing.
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

LONDON = ZoneInfo("Europe/London")
CALENDAR_TTL = 1800  # 30 minutes
TRAVEL_TTL = 900  # 15 minutes

TRANSCAPI_URL = "https://api.transcapi.com/v1/disruptions.json"
NH_CLOSURES_URL = "https://api.data.nationalhighways.co.uk/roads/v2.0/closures"
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
TUNNELS_LINK = "https://www.merseytravel.gov.uk/travel-updates/"
# Bbox around the Wirral + tunnel approaches + the A41 down to Chester.
WIRRAL_BBOX = "-3.25,53.2,-2.85,53.45"
NH_ROADS = {"M53", "M56"}

_lock = threading.Lock()
_calendar_cache = {"data": None, "fetched": 0}
_travel_cache = {"data": None, "fetched": 0}


def _not_configured():
    return {"status": "not_configured"}


def _error(message):
    return {"status": "error", "error": message}


# --- calendar ---

def parse_ics_events(ics_text, day=None):
    """Today's events from an iCal feed (recurrences expanded)."""
    import icalendar
    import recurring_ical_events

    if day is None:
        day = datetime.now(LONDON).date()
    day_start = datetime(day.year, day.month, day.day, tzinfo=LONDON)
    day_end = day_start + timedelta(days=1)
    calendar = icalendar.Calendar.from_ical(ics_text)
    events = []
    for event in recurring_ical_events.of(calendar).between(day_start, day_end):
        summary = event.get("SUMMARY")
        if summary is None:
            continue
        start_prop = event.get("DTSTART")
        end_prop = event.get("DTEND")
        if start_prop is None:
            continue
        start = start_prop.dt
        end = end_prop.dt if end_prop is not None else None
        all_day = isinstance(start, date) and not isinstance(start, datetime)
        if all_day:
            events.append({"summary": str(summary), "all_day": True, "start": None, "end": None})
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=LONDON)
        start = start.astimezone(LONDON)
        end_text = None
        if isinstance(end, datetime):
            if end.tzinfo is None:
                end = end.replace(tzinfo=LONDON)
            end_text = end.astimezone(LONDON).strftime("%H:%M")
        events.append({
            "summary": str(summary),
            "all_day": False,
            "start": start.strftime("%H:%M"),
            "end": end_text,
        })
    events.sort(key=lambda item: (item["start"] is None, item["start"] or ""))
    return events


def fetch_calendar(ics_url, day=None):
    if not ics_url:
        return _not_configured()
    try:
        response = requests.get(ics_url, timeout=15)
    except requests.RequestException:
        return _error("Could not reach the calendar feed.")
    if response.status_code != 200:
        return _error("The calendar feed refused the request.")
    try:
        events = parse_ics_events(response.text, day=day)
    except Exception:
        return _error("The calendar feed could not be read.")
    return {"status": "ok", "events": events}


def get_calendar(ics_url, day=None):
    now = time.time()
    with _lock:
        if _calendar_cache["data"] is not None and now - _calendar_cache["fetched"] < CALENDAR_TTL:
            return _calendar_cache["data"]
    result = fetch_calendar(ics_url, day=day)
    if result.get("status") == "ok":
        with _lock:
            _calendar_cache["data"] = result
            _calendar_cache["fetched"] = now
    return result


# --- rail (TransCAPI) ---

def parse_transcapi_disruptions(payload):
    """Disruption items from a TransCAPI /v1/disruptions.json reply."""
    if isinstance(payload, dict):
        items = payload.get("member") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    disruptions = []
    for item in items:
        if not isinstance(item, dict):
            continue
        summary = item.get("summary")
        if not summary:
            continue
        lines = []
        for line in item.get("lines") or []:
            if isinstance(line, dict) and line.get("line"):
                lines.append(str(line["line"]))
        disruptions.append({
            "summary": str(summary),
            "description": str(item.get("description") or ""),
            "advice": str(item.get("advice") or ""),
            "severity": str(item.get("severity") or "unknown"),
            "lines": lines,
            "url": item.get("url"),
        })
    # Wirral Line items first — they are the ones that decide his morning.
    disruptions.sort(key=lambda d: 0 if any("wirral" in line.lower() for line in d["lines"]) or "wirral" in d["summary"].lower() else 1)
    return disruptions


def fetch_rail(api_key):
    if not api_key:
        return _not_configured()
    try:
        response = requests.get(
            TRANSCAPI_URL,
            headers={"X-Api-Key": api_key},
            params={"mode": "rail", "operator": "Merseyrail", "limit": 20},
            timeout=15,
        )
    except requests.RequestException:
        return _error("Could not reach the rail service.")
    if response.status_code != 200:
        return _error("The rail service refused the request.")
    try:
        disruptions = parse_transcapi_disruptions(response.json())
    except ValueError:
        return _error("The rail service returned nothing usable.")
    return {"status": "ok", "disruptions": disruptions}


# --- roads: National Highways DATEX II ---

def _nh_record_road(record):
    """Road name from a DATEX II situation record, if it names one."""
    location = record.get("locationReference") or {}
    linear = location.get("locLinearLocation") or {}
    single = linear.get("locSingleRoadLinearLocation") or {}
    element = single.get("locLinearElementByCode") or {}
    road = element.get("roadName")
    if isinstance(road, str) and road.strip():
        return road.strip()
    return None


def _nh_record_text(record):
    comments = record.get("generalPublicComment") or []
    for comment in comments:
        if isinstance(comment, dict):
            text = comment.get("comment")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def parse_nh_closures(payload, roads=None, now=None):
    """Closures on the given roads from a DATEX II v2.0 reply.

    Trusts overallEndTime, not the status: finished closures stay
    "active" for up to 7 days after the works end.
    """
    roads = set(roads or NH_ROADS)
    now = now or datetime.now(LONDON)
    situations = []
    if isinstance(payload, dict):
        situations = payload.get("situation") or []
        if not situations:
            inner = payload.get("D2Payload") or payload.get("situationPublication") or {}
            if isinstance(inner, dict):
                situations = inner.get("situation") or []
    seen = set()
    closures = []
    for situation in situations:
        if not isinstance(situation, dict):
            continue
        for record in situation.get("situationRecord") or []:
            if not isinstance(record, dict):
                continue
            road = _nh_record_road(record)
            text = _nh_record_text(record)
            if road is None:
                for candidate in roads:
                    if candidate in text:
                        road = candidate
                        break
            if road not in roads:
                continue
            validity = record.get("validity") or {}
            spec = validity.get("validityTimeSpecification") or {}
            end_text = spec.get("overallEndTime")
            if end_text:
                try:
                    end = datetime.fromisoformat(str(end_text).replace("Z", "+00:00"))
                    if end.tzinfo is None:
                        end = end.replace(tzinfo=LONDON)
                    if end < now:
                        continue
                except ValueError:
                    pass
            key = (road, text)
            if key in seen:
                continue
            seen.add(key)
            closures.append({
                "road": road,
                "description": text or "Closure on " + road,
                "start": spec.get("overallStartTime"),
                "end": end_text,
            })
    return closures


def fetch_nh_closures(api_key, roads=None):
    if not api_key:
        return _not_configured()
    closures = []
    for closure_type in ("planned", "unplanned"):
        url = NH_CLOSURES_URL
        params = {"closureType": closure_type}
        for _page in range(3):
            try:
                response = requests.get(
                    url,
                    headers={
                        "Ocp-Apim-Subscription-Key": api_key,
                        "X-Response-MediaType": "application/json",
                    },
                    params=params,
                    timeout=15,
                )
            except requests.RequestException:
                return _error("Could not reach National Highways.")
            if response.status_code != 200:
                return _error("National Highways refused the request.")
            try:
                closures.extend(parse_nh_closures(response.json(), roads=roads))
            except ValueError:
                return _error("National Highways returned nothing usable.")
            next_url = response.headers.get("x-next")
            if not next_url:
                break
            url = next_url
            params = {}
    seen = set()
    unique = []
    for closure in closures:
        key = (closure["road"], closure["description"])
        if key not in seen:
            seen.add(key)
            unique.append(closure)
    return {"status": "ok", "closures": unique}


# --- roads: TomTom incidents (A41 + tunnel approaches) ---

def parse_tomtom_incidents(payload):
    """A41 and tunnel incidents from a TomTom incidentDetails reply."""
    incidents = []
    if not isinstance(payload, dict):
        return incidents
    for feature in payload.get("incidents") or []:
        props = feature.get("properties") or {}
        events = props.get("events") or []
        description = ""
        for event in events:
            if isinstance(event, dict) and event.get("description"):
                description = str(event["description"])
                break
        road_numbers = [str(road) for road in (props.get("roadNumbers") or [])]
        from_text = str(props.get("from") or "")
        to_text = str(props.get("to") or "")
        haystack = " ".join([description, from_text, to_text] + road_numbers).lower()
        is_a41 = "a41" in road_numbers or "a41" in haystack
        is_tunnel = "tunnel" in haystack
        if not (is_a41 or is_tunnel):
            continue
        delay = props.get("delay")
        incidents.append({
            "road": road_numbers[0] if road_numbers else ("A41" if is_a41 else "Tunnel"),
            "description": description or (from_text + " to " + to_text).strip() or "Incident reported",
            "from": from_text,
            "to": to_text,
            "delay_minutes": round(delay / 60) if isinstance(delay, (int, float)) else None,
            "tunnel": is_tunnel,
        })
    return incidents


def fetch_tomtom(api_key):
    if not api_key:
        return _not_configured()
    try:
        response = requests.get(
            TOMTOM_INCIDENTS_URL,
            params={"bbox": WIRRAL_BBOX, "key": api_key},
            timeout=15,
        )
    except requests.RequestException:
        return _error("Could not reach TomTom.")
    if response.status_code != 200:
        return _error("TomTom refused the request.")
    try:
        incidents = parse_tomtom_incidents(response.json())
    except ValueError:
        return _error("TomTom returned nothing usable.")
    return {"status": "ok", "incidents": incidents}


# --- combined travel ---

def fetch_travel(rail_key, nh_key, tomtom_key):
    rail = fetch_rail(rail_key)
    nh = fetch_nh_closures(nh_key)
    tomtom = fetch_tomtom(tomtom_key)
    tunnel_incidents = []
    if tomtom.get("status") == "ok":
        tunnel_incidents = [item for item in tomtom["incidents"] if item["tunnel"]]
    return {
        "rail": rail,
        "national_highways": nh,
        "tomtom": tomtom,
        "tunnels": {"link": TUNNELS_LINK, "incidents": tunnel_incidents},
    }


def get_travel(rail_key, nh_key, tomtom_key):
    now = time.time()
    with _lock:
        if _travel_cache["data"] is not None and now - _travel_cache["fetched"] < TRAVEL_TTL:
            return _travel_cache["data"]
    result = fetch_travel(rail_key, nh_key, tomtom_key)
    with _lock:
        _travel_cache["data"] = result
        _travel_cache["fetched"] = now
    return result
