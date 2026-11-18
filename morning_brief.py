"""FP104: morning brief for phone automation (MacroDroid / Tasker).

Builds the same "day at a glance" the Morning Hub shows, as JSON and as
short plain text, for delivery to Richie's phone. Two delivery paths share
one builder:

- Pull: GET /api/automation/brief (a Tasker HTTP Request action, or any
  client holding the cron token) returns the brief as JSON.
- Push: POST /api/automation/brief/send (triggered by cron-job.org on a
  morning schedule) POSTs the plain-text brief to the MacroDroid webhook
  URL in KAIVOR_MACRODROID_WEBHOOK_URL. MacroDroid's webhook trigger
  saves the POST body (up to 3800 chars) to a variable, so the text is
  capped well inside that limit.

Weather is fetched server-side from Open-Meteo for Puddington (the hub
fetches it client-side, so there is no server weather until this
milestone). One call per brief is far inside the free tier. Calendar and
travel reuse the FP103 fetchers and their caches.
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

LONDON = ZoneInfo("Europe/London")

# FP073 default place, kept in sync with the client.
PUDDINGTON = {"name": "Puddington, Wirral", "latitude": 53.25332, "longitude": -3.00877}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# MacroDroid webhook POST bodies cap at 3800 chars; stay well inside.
MAX_BRIEF_CHARS = 3500

BRIEF_STORY_COUNT = 5
BRIEF_TITLE_CHARS = 100
BRIEF_TASK_COUNT = 5

# WMO weather-code labels, matching the client's WEATHER_CODE_INFO.
WMO_TEXT = {
    0: ("Clear sky", "\u2600\ufe0f"),
    1: ("Mainly clear", "\U0001f324\ufe0f"),
    2: ("Partly cloudy", "\u26c5"),
    3: ("Overcast", "\u2601\ufe0f"),
    45: ("Fog", "\U0001f32b\ufe0f"),
    48: ("Depositing rime fog", "\U0001f32b\ufe0f"),
    51: ("Light drizzle", "\U0001f326\ufe0f"),
    53: ("Drizzle", "\U0001f326\ufe0f"),
    55: ("Dense drizzle", "\U0001f326\ufe0f"),
    56: ("Light freezing drizzle", "\U0001f327\ufe0f"),
    57: ("Dense freezing drizzle", "\U0001f327\ufe0f"),
    61: ("Slight rain", "\U0001f327\ufe0f"),
    63: ("Rain", "\U0001f327\ufe0f"),
    65: ("Heavy rain", "\U0001f327\ufe0f"),
    66: ("Light freezing rain", "\U0001f327\ufe0f"),
    67: ("Heavy freezing rain", "\U0001f327\ufe0f"),
    71: ("Slight snow", "\U0001f328\ufe0f"),
    73: ("Snow", "\U0001f328\ufe0f"),
    75: ("Heavy snow", "\U0001f328\ufe0f"),
    77: ("Snow grains", "\U0001f328\ufe0f"),
    80: ("Slight rain showers", "\U0001f326\ufe0f"),
    81: ("Rain showers", "\U0001f326\ufe0f"),
    82: ("Violent rain showers", "\U0001f326\ufe0f"),
    85: ("Slight snow showers", "\U0001f328\ufe0f"),
    86: ("Heavy snow showers", "\U0001f328\ufe0f"),
    95: ("Thunderstorm", "\u26c8\ufe0f"),
    96: ("Thunderstorm with slight hail", "\u26c8\ufe0f"),
    99: ("Thunderstorm with heavy hail", "\u26c8\ufe0f"),
}

_FX_KEYS = {"GBP_USD", "GBP_EUR", "EUR_USD", "GBP_JPY"}


def brief_greeting(hour):
    """Time-aware greeting, same bands as the hub's morningGreeting."""
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 18:
        return "Good afternoon"
    if 18 <= hour < 23:
        return "Good evening"
    return "Good night"


def format_finance_value(key, value):
    """A market value formatted like the homepage shows it (FP080)."""
    if key in _FX_KEYS:
        return f"{value:.4f}"
    return f"${value:,.2f}"


def fetch_brief_weather():
    """Current weather + today's range for Puddington, server-side."""
    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": PUDDINGTON["latitude"],
                "longitude": PUDDINGTON["longitude"],
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "Europe/London",
                "forecast_days": 1,
            },
            timeout=10,
        )
    except requests.RequestException:
        return {"status": "error", "error": "Could not reach Open-Meteo."}
    if response.status_code != 200:
        return {"status": "error", "error": "Open-Meteo refused the request."}
    try:
        data = response.json()
        current = data["current"]
        daily = data["daily"]
        code = int(current["weather_code"])
        text, icon = WMO_TEXT.get(code, ("Unknown", "\u2753"))
        return {
            "status": "ok",
            "place": PUDDINGTON["name"],
            "temp": round(float(current["temperature_2m"])),
            "feels": round(float(current["apparent_temperature"])),
            "condition": text,
            "icon": icon,
            "wind": round(float(current["wind_speed_10m"])),
            "high": round(float(daily["temperature_2m_max"][0])),
            "low": round(float(daily["temperature_2m_min"][0])),
            "rain_chance": daily["precipitation_probability_max"][0],
        }
    except (KeyError, TypeError, ValueError, IndexError):
        return {"status": "error", "error": "Open-Meteo returned nothing usable."}


def brief_top_stories(articles, count=BRIEF_STORY_COUNT):
    """First `count` articles with a title, as title + source pairs."""
    stories = []
    for article in articles or []:
        title = (article.get("title") or "").strip()
        if not title:
            continue
        stories.append(
            {
                "title": title,
                "source": (article.get("source") or article.get("publisher") or "").strip(),
            }
        )
        if len(stories) >= count:
            break
    return stories


def brief_markets(finance_data):
    """Gold / Bitcoin / GBP-USD snapshot, formatted like the hub."""
    picks = [("Gold", "Gold"), ("Bitcoin", "Bitcoin"), ("GBP_USD", "\u00a3 \u2192 $")]
    markets = []
    for key, label in picks:
        value = (finance_data or {}).get(key)
        if isinstance(value, (int, float)):
            markets.append({"label": label, "value": format_finance_value(key, value)})
    return markets


def brief_calendar_lines(calendar_result):
    """Today's events as plain lines; [] when none or unavailable."""
    if not isinstance(calendar_result, dict) or calendar_result.get("status") != "ok":
        return []
    lines = []
    for event in calendar_result.get("events") or []:
        summary = (event.get("summary") or "").strip()
        if not summary:
            continue
        if event.get("all_day"):
            lines.append(f"All day \u2014 {summary}")
        elif event.get("start"):
            span = event["start"] + (f"\u2013{event['end']}" if event.get("end") else "")
            lines.append(f"{span} {summary}")
        else:
            lines.append(summary)
    return lines


def brief_task_lines(tasks, today):
    """Open tasks due today or overdue, as plain lines; [] when none.

    `tasks` comes from the task store already sorted by due date then
    due time, so overdue items naturally come first. Undated tasks
    are not day-specific and are left out of the brief.
    """
    lines = []
    for task in tasks or []:
        if task.get("done"):
            continue
        due_date = task.get("due_date")
        if not due_date or due_date > today:
            continue
        title = (task.get("title") or "").strip()
        if not title:
            continue
        due_time = task.get("due_time") or ""
        if due_date < today:
            line = f"{title} \u2014 overdue (due {due_date})"
        elif due_time:
            line = f"{title} \u2014 due {due_time}"
        else:
            line = f"{title} \u2014 due today"
        lines.append(line)
        if len(lines) >= BRIEF_TASK_COUNT:
            break
    return lines


def brief_warning_lines(warnings_result):
    """Met Office warnings covering Puddington, as plain lines."""
    if not isinstance(warnings_result, dict) or warnings_result.get("status") != "ok":
        return []
    lines = []
    for warning in warnings_result.get("warnings") or []:
        level = warning.get("level") or ""
        types = ", ".join(warning.get("types") or [])
        headline = warning.get("headline") or "Weather warning"
        line = f"\u26a0\ufe0f {level} {types} \u2014 {headline}" if types else f"\u26a0\ufe0f {level} \u2014 {headline}"
        lines.append(line)
    return lines


def brief_travel_lines(travel_result):
    """Rail + roads + tunnel summary lines, mirroring the hub card."""
    result = travel_result or {}
    lines = []
    rail = result.get("rail") or {}
    if rail.get("status") == "ok":
        disruptions = rail.get("disruptions") or []
        if disruptions:
            for item in disruptions[:3]:
                lines.append(
                    "\U0001f686 " + (item.get("summary") or "Disruption")
                    + (" \u2014 severe" if item.get("severity") == "severe" else "")
                )
        else:
            lines.append("\U0001f686 Wirral Line \u2014 Good service")
    nh = result.get("national_highways") or {}
    tomtom = result.get("tomtom") or {}
    closures = nh.get("closures") or [] if nh.get("status") == "ok" else []
    incidents = tomtom.get("incidents") or [] if tomtom.get("status") == "ok" else []
    if nh.get("status") == "not_configured" and tomtom.get("status") == "not_configured":
        pass  # roads not set up; say nothing rather than a dead line
    elif not closures and not incidents and (
        nh.get("status") == "ok" or tomtom.get("status") == "ok"
    ):
        lines.append("\U0001f6e3\ufe0f M53 \u00b7 M56 \u00b7 A41 \u2014 No incidents")
    else:
        for item in closures[:3]:
            lines.append(
                "\U0001f6e3\ufe0f "
                + (item.get("road") or "Road")
                + ": "
                + (item.get("description") or "Closure")
            )
        for item in incidents[:3]:
            line = (
                "\U0001f6e3\ufe0f "
                + (item.get("road") or "Road")
                + ": "
                + (item.get("description") or "Incident")
            )
            if item.get("delay_minutes"):
                line += f" (delay ~{item['delay_minutes']} min)"
            lines.append(line)
    tunnels = (result.get("tunnels") or {}).get("incidents") or []
    for item in tunnels[:2]:
        lines.append("\U0001f687 Tunnel: " + (item.get("description") or "Incident"))
    return lines


def build_morning_brief(now, articles, finance_data, calendar_result, travel_result, weather, warnings=None, tasks=None):
    """Assemble the brief dict from already-fetched data (pure)."""
    greeting = brief_greeting(now.hour) + ", Richie"
    date_text = f"{now.strftime('%A')} {now.day} {now.strftime('%B %Y')}"
    return {
        "greeting": greeting,
        "date": now.date().isoformat(),
        "date_text": date_text,
        "generated_at": int(time.time()),
        "weather": weather or {"status": "error", "error": "Weather unavailable."},
        "warnings": brief_warning_lines(warnings),
        "stories": brief_top_stories(articles),
        "markets": brief_markets(finance_data),
        "calendar": brief_calendar_lines(calendar_result),
        "tasks": brief_task_lines(tasks, now.date().isoformat()),
        "travel": brief_travel_lines(travel_result),
    }


def format_brief_text(brief):
    """Plain-text brief for a phone notification, capped for MacroDroid."""
    parts = [f"{brief.get('greeting', 'Good morning, Richie')} \u2014 {brief.get('date_text', '')}"]
    weather = brief.get("weather") or {}
    if weather.get("status") == "ok":
        parts.append(
            f"\n{weather.get('icon', '')} {weather.get('place', '')}: "
            f"{weather.get('temp')}\u00b0 {weather.get('condition', '')} "
            f"(feels {weather.get('feels')}\u00b0), high {weather.get('high')}\u00b0 "
            f"low {weather.get('low')}\u00b0, rain {weather.get('rain_chance')}%, "
            f"wind {weather.get('wind')} km/h"
        )
    else:
        parts.append("\nWeather unavailable.")
    warnings = brief.get("warnings") or []
    if warnings:
        parts.append("\nWarnings:")
        parts.extend(f"\u2022 {line}" for line in warnings)
    stories = brief.get("stories") or []
    if stories:
        parts.append("\nTop stories:")
        for story in stories:
            title = story["title"]
            if len(title) > BRIEF_TITLE_CHARS:
                title = title[: BRIEF_TITLE_CHARS - 1] + "\u2026"
            source = f" ({story['source']})" if story.get("source") else ""
            parts.append(f"\u2022 {title}{source}")
    markets = brief.get("markets") or []
    if markets:
        parts.append("\nMarkets: " + ", ".join(f"{m['label']} {m['value']}" for m in markets))
    calendar = brief.get("calendar") or []
    if calendar:
        parts.append("\nToday:")
        parts.extend(f"\u2022 {line}" for line in calendar)
    else:
        parts.append("\nNothing on today.")
    tasks = brief.get("tasks") or []
    if tasks:
        parts.append("\nTasks today:")
        parts.extend(f"\u2022 {line}" for line in tasks)
    travel = brief.get("travel") or []
    if travel:
        parts.append("\nTravel:")
        parts.extend(f"\u2022 {line}" for line in travel)
    text = "\n".join(parts)
    if len(text) > MAX_BRIEF_CHARS:
        text = text[: MAX_BRIEF_CHARS - 1] + "\u2026"
    return text


def send_brief_to_webhook(webhook_url, text):
    """POST the brief text to the MacroDroid webhook trigger URL."""
    if not webhook_url:
        return {"ok": False, "error": "MacroDroid webhook URL is not configured."}
    if not webhook_url.startswith("https://"):
        return {"ok": False, "error": "MacroDroid webhook URL must be https."}
    try:
        response = requests.post(
            webhook_url,
            data=text.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            timeout=15,
        )
    except requests.RequestException:
        return {"ok": False, "error": "Could not reach the MacroDroid webhook."}
    if response.status_code != 200:
        return {"ok": False, "error": f"MacroDroid refused the request ({response.status_code})."}
    return {"ok": True, "status": response.status_code}
