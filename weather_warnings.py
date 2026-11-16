"""FP106: Met Office Weather Warnings for Puddington.

Reads the National Severe Weather Warnings Service (NSWWS) API:
an Atom feed entry point, then the GeoJSON "issued" collection it
links to (rel="related"). Two signup routes give the same shape —
v1.0 via the Met Office contact form (key in the `x-api-key`
header) and v1.1 via the Weather DataHub (key in the `apikey`
header) — so both headers are sent with the same key and the feed
URL + key are config (KAIVOR_WARNINGS_FEED_URL,
KAIVOR_WARNINGS_API_KEY). Docs verified 16 Nov 2026:
metoffice.github.io/nswws-public-api/ (v1.0) and
datahub.metoffice.gov.uk/docs/g/category/warnings/overview (v1.1).

Warnings are filtered to the ones whose polygon actually covers
Puddington (point-in-polygon on the MultiPolygon outer rings) —
a warning for Cumbria must not alert him just because it shares
the North West region. The collection covers the next 7 days, so
future warnings are shown too, with their valid from/to times.
Results are cached for 15 minutes, like travel.
"""

import time
import xml.etree.ElementTree as ET

import requests

PUDDINGTON_LAT = 53.25332
PUDDINGTON_LON = -3.00877

WARNINGS_TTL = 900

LEVEL_ORDER = {"RED": 0, "AMBER": 1, "YELLOW": 2}

_WARNINGS_CACHE = {"data": None, "fetched_at": 0}

_ATOM_NS = "http://www.w3.org/2005/Atom"


class WarningsError(Exception):
    """The warnings feed or GeoJSON call failed."""


def point_in_polygon(lat, lon, ring):
    """Ray casting: is (lat, lon) inside a ring of [lon, lat] points?"""
    inside = False
    count = len(ring)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        # Edge straddles the horizontal line through the point, and
        # the point is left of the edge's crossing x.
        if (yi > lat) != (yj > lat):
            crossing_x = xi + (lat - yi) * (xj - xi) / (yj - yi)
            if lon < crossing_x:
                inside = not inside
        j = i
    return inside


def point_in_multipolygon(lat, lon, multipolygon):
    """True when any polygon's outer ring contains the point.

    Holes are ignored on purpose: a hole would mean "not warned"
    inside it, and for warnings the safe error is to show it.
    """
    for polygon in multipolygon or []:
        if not polygon:
            continue
        if point_in_polygon(lat, lon, polygon[0]):
            return True
    return False


def parse_atom_related_link(feed_xml):
    """The 'related' link href at the head of the Atom feed.

    That link is the GeoJSON "issued" collection, and its URL
    changes every time the feed updates — always follow it fresh.
    """
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise WarningsError("The warnings feed was not valid XML.") from exc
    for tag in (f"{{{_ATOM_NS}}}link", "link"):
        for link in root.findall(tag):
            if link.get("rel") == "related" and link.get("href"):
                return link.get("href")
    raise WarningsError("The warnings feed had no latest-warnings link.")


def parse_warnings(feature_collection, lat=PUDDINGTON_LAT, lon=PUDDINGTON_LON):
    """Features covering (lat, lon), mapped + sorted by level then date."""
    features = (feature_collection or {}).get("features") or []
    warnings = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "MultiPolygon":
            continue
        if not point_in_multipolygon(lat, lon, geometry.get("coordinates")):
            continue
        level = str(props.get("warningLevel") or "").upper()
        warnings.append(
            {
                "level": level,
                "types": [str(t) for t in (props.get("weatherType") or []) if t],
                "headline": (props.get("warningHeadline") or "").strip(),
                "valid_from": props.get("validFromDate"),
                "valid_to": props.get("validToDate"),
                "impact": props.get("warningImpact"),
                "likelihood": props.get("warningLikelihood"),
                "what_to_expect": [
                    str(item) for item in (props.get("whatToExpect") or []) if item
                ][:3],
                "further_details": (props.get("warningFurtherDetails") or "").strip(),
                "areas": [
                    str(area.get("regionName"))
                    for area in (props.get("affectedAreas") or [])
                    if isinstance(area, dict) and area.get("regionName")
                ],
                "warning_id": props.get("warningId"),
            }
        )
    warnings.sort(
        key=lambda w: (LEVEL_ORDER.get(w["level"], 9), w["valid_from"] or "")
    )
    return warnings


def _headers(api_key):
    # v1.0 reads x-api-key, DataHub v1.1 reads apikey; sending both
    # with the same value works for either signup route.
    return {"x-api-key": api_key, "apikey": api_key}


def fetch_warnings(feed_url, api_key):
    """Full chain: feed -> related link -> GeoJSON -> Puddington filter."""
    if not feed_url or not api_key:
        return {"status": "not_configured"}
    try:
        feed_response = requests.get(feed_url, headers=_headers(api_key), timeout=15)
    except requests.RequestException:
        return {"status": "error", "error": "Could not reach the warnings feed."}
    if feed_response.status_code == 403:
        return {"status": "error", "error": "The Met Office refused the warnings key."}
    if feed_response.status_code != 200:
        return {"status": "error", "error": "The warnings feed refused the request."}
    try:
        issued_url = parse_atom_related_link(feed_response.text)
    except WarningsError as exc:
        return {"status": "error", "error": str(exc)}
    try:
        geo_response = requests.get(issued_url, headers=_headers(api_key), timeout=15)
    except requests.RequestException:
        return {"status": "error", "error": "Could not reach the warnings data."}
    if geo_response.status_code != 200:
        return {"status": "error", "error": "The warnings data refused the request."}
    try:
        collection = geo_response.json()
    except ValueError:
        return {"status": "error", "error": "The warnings data was not valid JSON."}
    return {"status": "ok", "warnings": parse_warnings(collection)}


def get_warnings(feed_url, api_key):
    """Cached fetch (15 min). Errors are cached too, like travel."""
    now = time.time()
    if _WARNINGS_CACHE["data"] is not None and now - _WARNINGS_CACHE["fetched_at"] < WARNINGS_TTL:
        return _WARNINGS_CACHE["data"]
    result = fetch_warnings(feed_url, api_key)
    _WARNINGS_CACHE["data"] = result
    _WARNINGS_CACHE["fetched_at"] = now
    return result
