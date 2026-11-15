"""Stock photo fallback (FP089).

For articles with no publisher picture, Kaivor takes keywords from
the headline and fetches a matching free stock photo from the
Openverse API (api.openverse.org). Openverse needs no API key for
basic use. Results are cached per query so a headline (or another
headline with the same keywords) only ever costs one lookup.

The caller (main.py's /api/stock_image route) is the only thing that
talks to this module. Nothing here ever raises into a request:
any failure returns None and the card stays text-only.
"""

import re
import time
from collections import OrderedDict
from urllib.parse import urlparse

import requests

OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
OPENVERSE_TIMEOUT_SECONDS = 10
OPENVERSE_USER_AGENT = "KaivorNews/1.0 (personal news app)"

_STOCK_CACHE_MAX_ENTRIES = 200
_STOCK_FAILURE_TTL_SECONDS = 60

_MISSING = object()

# Words that carry no picture meaning in a headline. "new" is
# deliberately NOT here: dropping it would break "New Zealand",
# "New York" and other proper names, and the FP089.1 fallback chain
# makes a weak word harmless.
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "with", "after", "as", "at", "by", "from", "into", "over",
    "under", "about", "is", "are", "was", "were", "be", "been",
    "it", "its", "he", "she", "they", "his", "her", "their",
    "this", "that", "these", "those", "what", "when", "where",
    "who", "why", "how", "not", "but", "says", "said",
    "one", "two", "first",
})

_LICENSE_LABELS = {
    "by": "CC BY",
    "by-sa": "CC BY-SA",
    "by-nc": "CC BY-NC",
    "by-nd": "CC BY-ND",
    "by-nc-sa": "CC BY-NC-SA",
    "by-nc-nd": "CC BY-NC-ND",
    "cc0": "CC0",
    "pdm": "Public Domain",
}

# Normalised query -> (result dict or None, timestamp). Positive
# results live for the life of the process; failures are retried
# after _STOCK_FAILURE_TTL_SECONDS.
_cache: "OrderedDict[str, tuple]" = OrderedDict()


def keywords_from_headline(title):
    """Picture-worthy words from a headline, in headline order.

    Leading/trailing quote marks are stripped ("here'" from a quoted
    headline becomes "here"); internal apostrophes stay ("We've").
    """
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", str(title or ""))
    cleaned = [w.strip("'") for w in words]
    return [w for w in cleaned if len(w) >= 3 and w.lower() not in _STOPWORDS]


def _candidate_queries(words):
    """Query attempts for a headline's keywords, most specific first.

    Openverse matches all terms, so a five-word query usually returns
    nothing for a news headline (verified live 15 Nov 2026: "We've
    waited years here Wales" -> 0 results, "Wales New Zealand" ->
    240). Try the full set first (best match when it works), then
    the proper nouns, then the single most distinctive word.
    """
    if not words:
        return []
    candidates = [" ".join(words[:5])]
    # Proper nouns: capitalised words other than the first, which is
    # capitalised by headline convention ("We've waited..." — "We've"
    # is not a place). If the first word is the only capitalised one,
    # it is the best guess available ("Wales win the cup").
    proper = [w for w in words[1:] if w and w[0].isupper()]
    if not proper and words[0] and words[0][0].isupper():
        proper = [words[0]]
    if proper:
        joined = " ".join(proper)
        if joined.lower() != candidates[0].lower():
            candidates.append(joined)
    pool = proper or words
    best = max(pool, key=len)
    if best.lower() not in [c.lower() for c in candidates]:
        candidates.append(best)
    return candidates


def _normalise_query(query):
    return " ".join(str(query or "").lower().split())


def _clean_url(value):
    url = str(value or "").strip()
    if len(url) > 2048:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return url


def _credit_for(item):
    """Attribution line, e.g. "Jane Doe · CC BY 2.0"."""
    creator = str(item.get("creator") or "").strip()
    slug = str(item.get("license") or "").strip().lower()
    label = _LICENSE_LABELS.get(slug, slug.upper() if slug else "")
    version = str(item.get("license_version") or "").strip()
    if label and version:
        label = "{} {}".format(label, version)
    if creator and label:
        return "{} · {}".format(creator, label)
    return creator or label or ""


def _cache_get(key):
    entry = _cache.get(key)
    if entry is None:
        return _MISSING
    value, stored_at = entry
    if value is None and time.time() - stored_at > _STOCK_FAILURE_TTL_SECONDS:
        del _cache[key]
        return _MISSING
    return value


def _cache_put(key, value):
    _cache[key] = (value, time.time())
    _cache.move_to_end(key)
    while len(_cache) > _STOCK_CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


def _fetch_from_openverse(query):
    try:
        res = requests.get(
            OPENVERSE_API_URL,
            params={"q": query, "page_size": 1,
                    "license_type": "commercial"},
            headers={"User-Agent": OPENVERSE_USER_AGENT},
            timeout=OPENVERSE_TIMEOUT_SECONDS,
        )
        if res.status_code != 200:
            return None
        results = (res.json() or {}).get("results") or []
        if not results:
            return None
        url = _clean_url(results[0].get("url"))
        if not url:
            return None
        return {"url": url, "credit": _credit_for(results[0]),
                "query": query}
    except Exception:
        return None


def get_stock_image(headline):
    """Best Openverse image for a headline, or None.

    Returns {"url", "credit", "query"} on a hit. Tries the candidate
    queries in order and returns the first hit. Each attempt is cached
    under its own query, and the final result is also cached under the
    headline's full query so a repeat headline costs no new lookup.
    """
    words = keywords_from_headline(headline)
    if not words:
        return None
    full_key = _normalise_query(" ".join(words[:5]))
    hit = _cache_get(full_key)
    if hit is not _MISSING:
        return hit
    result = None
    for query in _candidate_queries(words):
        key = _normalise_query(query)
        cached = _cache_get(key)
        if cached is not _MISSING:
            result = cached
            if result is not None:
                break
            continue
        result = _fetch_from_openverse(query)
        _cache_put(key, result)
        if result is not None:
            break
    _cache_put(full_key, result)
    return result
