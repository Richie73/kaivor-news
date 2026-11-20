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
# FP089.2: fetch several candidates per query and pick the best
# match — taking the first result is how a bulldog ended up on an
# NFL story (15 Nov 2026).
OPENVERSE_PAGE_SIZE = 5

_STOCK_CACHE_MAX_ENTRIES = 200
_STOCK_FAILURE_TTL_SECONDS = 60

_MISSING = object()

# Words that pass the stopword filter but are too generic to prove
# a photo matches its headline. The FP089.2 live check (15 Nov 2026)
# showed why each group is here: a boxer photo tagged "black",
# "friday" and "pro" matched a Black Friday screwdriver story, and
# a TV cartoon titled "What are you watching tonight: Sunday show,
# NFL or #Emmys?" matched an NHL story on "tonight" and "sunday".
_SCORING_EXCLUDE = frozenset({
    # Days of the week and time words.
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "today", "tomorrow", "yesterday",
    "tonight", "weekend", "morning", "evening", "night",
    "daily", "weekly",
    # Colours: a black-and-white photo is not a photo about "black".
    "black", "white", "red", "blue", "green", "yellow", "orange",
    "purple", "pink", "brown", "grey", "gray",
    # Number words.
    "three", "four", "five", "six", "seven", "eight", "nine",
    "ten",
    # Weak verbs and fillers.
    "new", "news", "year", "years", "week", "time", "first", "last",
    "next", "back", "more", "way", "top", "find", "finding",
    "finds", "found", "make", "makes", "take", "takes", "get",
    "gets", "got", "set", "put", "say", "says", "said", "man",
    "woman", "people", "person", "pro", "off", "run", "run-up",
    "follow", "live", "face", "here", "there", "watch", "show",
    "shows", "look", "see", "sees", "come", "comes", "going",
    "goes",
})

# Words dropped from the SEARCH queries as well as the scoring.
# "new" is the exception: it is too weak to score on (any photo of
# New York would match), but dropping it from queries would break
# "New Zealand" and "New York" — "Wales Zealand" is a worse query
# than "Wales New Zealand".
_QUERY_EXCLUDE = _SCORING_EXCLUDE - {"new"}
# title or tag proves little on its own — the NHL cartoon passed
# FP089.2 because its title mentioned "NFL" as one TV option among
# several — so an acronym-only category match needs a keyword
# match alongside it (see _image_passes).
_CATEGORY_ACRONYMS = frozenset({
    "nfl", "nba", "mlb", "nhl", "fifa", "uefa", "ufc", "mma",
    "ai", "nasa", "dna",
})

# FP089.2: topical words per news category. For a gated category a
# photo must match at least one of these words, or match two or more
# headline keywords — one keyword alone is not enough (a lion in
# Egypt is not the Detroit Lions). World, UK and Culture are too
# broad to gate, so they need one keyword match only.
# FP089.3: words that are common in unrelated photo tags are pruned
# ("digital" is on half of Flickr, "cloud" is on sky photos, "game"
# is on video games and board games, "cup"/"belt"/"ring" are on
# kitchenware and jewellery, "star" is on celebrities).
_CATEGORY_WORDS = {
    "Sport": {
        "football", "soccer", "rugby", "cricket", "tennis", "golf",
        "hockey", "baseball", "basketball", "boxing", "ufc", "mma",
        "wrestling", "stadium", "match", "player", "team",
        "ball", "sport", "athlete", "championship", "league",
        "goal", "race", "racing", "olympic", "medal", "coach",
        "club", "pitch", "court", "trophy",
        "score", "season", "draft", "quarterback", "touchdown",
        "nfl", "nba", "mlb", "nhl", "fifa", "uefa", "tournament",
    },
    "Technology": {
        "computer", "phone", "smartphone", "software", "hardware",
        "robot", "artificial", "intelligence", "tech",
        "screen", "code", "app", "internet", "data", "cyber",
        "chip", "device", "gadget", "laptop", "tablet", "network",
        "algorithm", "learning", "electric",
        "battery", "drone", "satellite", "ai", "computing",
        "server", "servers",
    },
    "Android": {
        "computer", "phone", "smartphone", "software", "hardware",
        "robot", "artificial", "intelligence", "tech",
        "screen", "code", "app", "internet", "data", "cyber",
        "chip", "device", "gadget", "laptop", "tablet", "network",
        "algorithm", "learning", "electric",
        "battery", "drone", "satellite", "ai", "android",
        "computing", "server", "servers",
    },
    "Science": {
        "science", "space", "planet", "research", "lab",
        "laboratory", "experiment", "scientist", "nature",
        "animal", "bird", "fish", "plant", "tree", "forest",
        "ocean", "sea", "climate", "weather", "earth", "moon",
        "mars", "nasa", "telescope", "microscope", "dna", "gene",
        "virus", "vaccine", "medicine", "medical", "health",
        "doctor", "hospital",
    },
    "Business": {
        "money", "finance", "market", "stock", "shares", "bank",
        "banking", "business", "trade", "economy", "economic",
        "price", "prices", "cost", "tax", "company", "corporate",
        "investor", "investment", "profit", "loss", "jobs",
        "employment", "worker", "factory", "shop", "store",
        "retail", "oil", "gas", "energy",
    },
}
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
    "one", "two", "first", "go", "up", "do", "so", "no",
})

# Two-letter words that are safe to search and score on. Most
# two-letter words are ambiguous ("AD" is an Athletic Director in a
# headline and an advertisement in a photo tag — a Levi's mural
# titled "Levi's Ad, Utah" matched a Utah football story on "ad"
# plus "utah" in FP089.3's live check; "PM" is a Prime Minister
# or an afternoon, "MP" is a Member of Parliament or megapixels).
# Only these six are unambiguous enough to keep.
_TWO_LETTER_KEYWORDS = frozenset({"ai", "uk", "us", "tv", "eu", "un"})

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

# Categories that never get a stock photo (FP128): puzzle cards are
# links to puzzle apps, not stories — a guessed photo can only
# misfire (20 Nov 2026: a water-park "challenge" photo on the
# Wordle card, matched on the word "Challenge" alone, because
# "Puzzles" is ungated and one keyword hit passes).
_NO_STOCK_CATEGORIES = frozenset({"puzzles"})

# Normalised query -> (result dict or None, timestamp). Positive
# results live for the life of the process; failures are retried
# after _STOCK_FAILURE_TTL_SECONDS.
_cache: "OrderedDict[str, tuple]" = OrderedDict()


def keywords_from_headline(title):
    """Picture-worthy words from a headline, in headline order.

    Leading/trailing quote marks are stripped ("here'" from a quoted
    headline becomes "here"); internal apostrophes stay ("We've").
    Two-letter words count only when they are in
    _TWO_LETTER_KEYWORDS (FP089.4): most are ambiguous ("AD" is an
    Athletic Director in a headline and an advertisement in a photo
    tag), so only AI, UK, US, TV, EU and UN survive.
    """
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", str(title or ""))
    cleaned = [w.strip("'") for w in words]
    return [w for w in cleaned
            if len(w) >= 2
            and w.lower() not in _STOPWORDS
            and (len(w) > 2 or w.lower() in _TWO_LETTER_KEYWORDS)]


def _distinctive_words(words):
    """Words worth searching for and scoring on: everything the
    query exclusion list drops is too generic to prove a photo
    matches (a photo tagged "friday" is not a photo about the
    story). Possessives are normalised first ("Sunday's" is the
    day "sunday", not a distinctive word)."""
    distinctive = []
    for word in words:
        base = word.lower().rstrip("'").removesuffix("'s")
        if base not in _QUERY_EXCLUDE:
            distinctive.append(word)
    return distinctive


def _candidate_queries(words):
    """Query attempts for a headline's keywords, most specific first.

    Openverse matches all terms, so a five-word query usually returns
    nothing for a news headline (verified live 15 Nov 2026: "We've
    waited years here Wales" -> 0 results, "Wales New Zealand" ->
    240). Try the full set first (best match when it works), then
    the proper nouns, then the single most distinctive word: an
    all-caps acronym (NHL, NFL) if there is one, else the longest
    word (FP089.3 — an acronym is the most distinctive word in a
    headline, and the longest word beats a niche brand name:
    "screwdriver" beats "Fanttik").
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
    acronyms = [w for w in words if w.isupper() and len(w) >= 2]
    if acronyms:
        best = max(acronyms, key=len)
    else:
        best = max(words, key=len)
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


def _item_words(item):
    """Lowercase word set from an Openverse result's title, tags and
    description. Tags arrive as [{"name": ...}] or plain strings."""
    text = str(item.get("title") or "") + " " + str(item.get("description") or "")
    for tag in item.get("tags") or []:
        if isinstance(tag, dict):
            text += " " + str(tag.get("name") or "")
        else:
            text += " " + str(tag or "")
    return set(re.findall(r"[a-z]+", text.lower()))


def _keyword_matches(words, keywords):
    """Distinct headline keywords present as whole words. A trailing
    's' is forgiven either way, so 'lions' matches a photo titled
    'lion' and 'lion' matches one tagged 'lions'. Matching is on
    whole words, not substrings — 'patriots' must not match a photo
    titled 'patriotic' (that is how the bulldog got through)."""
    hits = set()
    for keyword in keywords:
        word = keyword.lower().rstrip("'").removesuffix("'s")
        if word in _SCORING_EXCLUDE or len(word) < 2:
            continue
        forms = {word, word + "s"}
        if word.endswith("s"):
            forms.add(word[:-1])
        if forms & words:
            hits.add(word)
    return hits


def _score_image(item, keywords, category):
    """(keyword_hits, category_hits) for one Openverse result."""
    words = _item_words(item)
    keyword_hits = _keyword_matches(words, keywords)
    category_hits = set()
    allowed = _CATEGORY_WORDS.get(category or "")
    if allowed:
        category_hits = {w for w in allowed if w in words}
    return keyword_hits, category_hits


def _image_passes(item, keywords, category):
    """Does this photo belong with its headline? For a gated
    category (Sport, Technology, Android, Science, Business) it
    passes when a full topical word matches (a photo tagged
    "football" is a photo about football), or when two headline
    keywords match, or when one keyword matches alongside an
    acronym-only category match (a photo tagged "nfl" for a story
    that says "NFL"). A bare acronym alone does NOT pass: the NHL
    cartoon passed FP089.2 because its title mentioned "NFL" as
    one TV option among several. Ungated categories (World, UK,
    Culture) need one keyword match. A photo that passes nothing
    is worse than no photo at all."""
    keyword_hits, category_hits = _score_image(item, keywords, category)
    if category not in _CATEGORY_WORDS:
        return len(keyword_hits) >= 1
    topical = {w for w in category_hits if w not in _CATEGORY_ACRONYMS}
    if topical:
        return True
    if category_hits and keyword_hits:
        return True
    return len(keyword_hits) >= 2


def _fetch_from_openverse(query, keywords, category=None):
    try:
        res = requests.get(
            OPENVERSE_API_URL,
            params={"q": query, "page_size": OPENVERSE_PAGE_SIZE,
                    "license_type": "commercial"},
            headers={"User-Agent": OPENVERSE_USER_AGENT},
            timeout=OPENVERSE_TIMEOUT_SECONDS,
        )
        if res.status_code != 200:
            return None
        best = None
        best_score = -1
        for item in (res.json() or {}).get("results") or []:
            if not _image_passes(item, keywords, category):
                continue
            url = _clean_url(item.get("url"))
            if not url:
                continue
            keyword_hits, category_hits = _score_image(item, keywords, category)
            score = len(keyword_hits) + len(category_hits)
            if score > best_score:
                best_score = score
                best = {"url": url, "credit": _credit_for(item),
                        "query": query}
        return best
    except Exception:
        return None


def get_stock_image(headline, category=None):
    """Best Openverse image for a headline, or None.

    Returns {"url", "credit", "query"} on a hit. Tries the candidate
    queries in order and returns the first hit. Each attempt is cached
    under its own query, and the final result is also cached under the
    headline's full query, so a repeat headline costs no new lookup.
    The category gates relevance (see _image_passes) and is part of
    the cache key, so the same words in different categories score
    independently. FP089.3: the queries and the scoring both use
    only the distinctive words — generic words ("friday", "tonight",
    "black") drove the FP089.2 mismatches by fetching and matching
    unrelated photos.
    """
    if (category or "").strip().lower() in _NO_STOCK_CATEGORIES:
        return None
    words = keywords_from_headline(headline)
    distinctive = _distinctive_words(words)
    if not distinctive:
        return None
    category = category or ""
    full_key = (_normalise_query(" ".join(distinctive[:5]))
                + "|" + category.lower())
    hit = _cache_get(full_key)
    if hit is not _MISSING:
        return hit
    result = None
    for query in _candidate_queries(distinctive):
        key = _normalise_query(query) + "|" + category.lower()
        cached = _cache_get(key)
        if cached is not _MISSING:
            result = cached
            if result is not None:
                break
            continue
        result = _fetch_from_openverse(query, distinctive, category)
        _cache_put(key, result)
        if result is not None:
            break
    _cache_put(full_key, result)
    return result
