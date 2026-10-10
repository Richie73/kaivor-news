import os
import re
import threading
import time
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse

import feedparser
import requests
from flask import Flask, jsonify, render_template, request, send_from_directory

from evidence_engine import evidence_sentence
from story_intelligence import enrich_articles
from story_timeline import build_story_timeline
from importance_engine import build_importance_model
from personal_relevance import load_profile, save_profile, calculate_personal_relevance

from news_store import (
    deduplicate_articles,
    is_saved,
    load_custom_sources,
    load_saved_articles,
    load_secrets,
    remove_saved_article,
    save_article,
    save_custom_sources,
    save_secret,
)

app = Flask(__name__)


def display_date(value):
    """Render stored UTC ISO timestamps as UK-local user-facing dates."""
    if not value:
        return ""
    try:
        raw = str(value).strip()
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone()
        return dt.strftime("%d %b %Y · %H:%M")
    except Exception:
        return str(value)


app.jinja_env.filters["display_date"] = display_date

_finance_cache = {"data": {}, "last_updated": 0}
_cache_lock = threading.Lock()
_news_cache = {"articles": [], "last_updated": 0}
_news_lock = threading.Lock()

# Background cron refresh state. The public cron endpoint must return
# immediately because cron-job.org has a 30-second response limit.
_cron_refresh_lock = threading.Lock()
_cron_refresh_state = {
    "running": False,
    "started_at": 0.0,
    "last_completed": 0.0,
    "last_count": 0,
    "last_error": "",
}

DEFAULT_RSS_SOURCES = {}


def build_rss_sources():
    """Compatibility view of the curated multi-source feed registry."""
    from news_freshness import build_feed_registry
    return {category: [feed["url"] for feed in feeds] for category, feeds in build_feed_registry(load_custom_sources()).items()}


def load_persisted_secrets() -> None:
    secrets = load_secrets()
    aliases = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "guardian": "GUARDIAN_API_KEY",
        "brave": "BRAVE_API_KEY",
    }
    for key, env_name in aliases.items():
        if secrets.get(key):
            os.environ.setdefault(env_name, secrets[key])


# Finance refresh is deliberately on-demand: it must never compete with RSS refreshes.
_finance_refresh_lock = threading.Lock()
_finance_refresh_state = {
    "running": False,
    "started_at": 0.0,
    "last_completed": 0.0,
    "last_error": "",
    "last_updated_keys": [],
}


def _fetch_finance_data():
    """Fetch available market data with bounded connect/read timeouts."""
    data = {}
    errors = []

    # FX data: one request for GBP pairs and one for EUR/USD.
    fx_requests = (
        ("https://api.frankfurter.app/latest?from=GBP&to=USD,EUR", {"GBP_USD": "USD", "GBP_EUR": "EUR"}),
        ("https://api.frankfurter.app/latest?from=EUR&to=USD", {"EUR_USD": "USD"}),
    )
    for url, mapping in fx_requests:
        try:
            response = requests.get(url, timeout=(3, 5))
            response.raise_for_status()
            rates = response.json().get("rates", {})
            for output_key, rate_key in mapping.items():
                value = rates.get(rate_key)
                if value is not None:
                    data[output_key] = float(value)
        except Exception as exc:
            errors.append(f"FX: {type(exc).__name__}")

    symbols = {
        "Brent_Oil": "BZ=F",
        "Gold": "GC=F",
        "Bitcoin": "BTC-USD",
        "SP500": "^GSPC",
    }
    headers = {"User-Agent": "Mozilla/5.0 Kaivor-News/FP018.2"}
    for key, symbol in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
            response = requests.get(url, headers=headers, timeout=(3, 5))
            response.raise_for_status()
            results = response.json().get("chart", {}).get("result", [])
            if results:
                meta = results[0].get("meta", {})
                price = meta.get("regularMarketPrice") or meta.get("previousClose")
                if price is not None:
                    data[key] = float(round(float(price), 2))
        except Exception as exc:
            errors.append(f"{key}: {type(exc).__name__}")

    return data, errors


def _finance_refresh_worker():
    """Perform one isolated refresh; preserve existing values if a source fails."""
    try:
        fresh_data, errors = _fetch_finance_data()
        with _cache_lock:
            if fresh_data:
                merged = dict(_finance_cache.get("data") or {})
                merged.update(fresh_data)
                _finance_cache["data"] = merged
                _finance_cache["last_updated"] = time.time()
        with _finance_refresh_lock:
            _finance_refresh_state["last_completed"] = time.time()
            _finance_refresh_state["last_error"] = "; ".join(errors[:3]) if errors else ("No providers returned data" if not fresh_data else "")
            _finance_refresh_state["last_updated_keys"] = sorted(fresh_data.keys())
    except Exception as exc:
        with _finance_refresh_lock:
            _finance_refresh_state["last_completed"] = time.time()
            _finance_refresh_state["last_error"] = type(exc).__name__
    finally:
        with _finance_refresh_lock:
            _finance_refresh_state["running"] = False


def background_finance_worker():
    """Legacy compatibility wrapper; intentionally does not run a loop."""
    _finance_refresh_worker()


def clean_html(raw_html):
    text = re.sub(r"<.*?>", " ", raw_html or "")
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 160:
        text = text[:157] + "..."
    return text


def source_name_from_url(url: str, fallback: str) -> str:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        return host.split(".")[0].replace("feeds", "BBC").title() or fallback
    except Exception:
        return fallback


def find_rss_via_brave(query):
    brave_key = os.environ.get("BRAVE_API_KEY")
    if not brave_key:
        return None
    try:
        headers = {"X-Subscription-Token": brave_key}
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": f"{query} RSS feed URL"},
            headers=headers,
            timeout=5,
        )
        if response.status_code == 200:
            results = response.json().get("web", {}).get("results", [])
            for result in results:
                link = result.get("url", "")
                if "rss" in link.lower() or "feed" in link.lower() or ".xml" in link.lower():
                    return link
            if results:
                return results[0].get("url")
    except Exception:
        pass
    return None


def _published_timestamp(value):
    try:
        text = str(value or "").strip()
        if not text:
            return 0
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except (TypeError, ValueError):
        return 0


def fetch_guardian_articles(category):
    articles = []
    guardian_key = os.environ.get("GUARDIAN_API_KEY")
    if not guardian_key:
        return articles
    section_map = {"World": "world", "Technology": "technology", "Business": "business", "Science": "science", "UK": "uk-news", "Sport": "sport"}
    section = section_map.get(category)
    if not section:
        return articles
    try:
        url = (
            "https://content.guardianapis.com/search"
            f"?section={section}&api-key={guardian_key}&show-fields=trailText"
        )
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            results = response.json().get("response", {}).get("results", [])
            for item in results[:5]:
                fields = item.get("fields", {})
                articles.append(
                    {
                        "title": item.get("webTitle", "Guardian Article"),
                        "description": clean_html(fields.get("trailText", "Guardian coverage update.")),
                        "category": category,
                        "source": "The Guardian",
                        "published": item.get("webPublicationDate", "Recent")[:16],
                        "published_ts": _published_timestamp(item.get("webPublicationDate")),
                        "link": item.get("webUrl", "#"),
                        "feed_tier": "primary",
                        "feed_url": "https://content.guardianapis.com/search",
                    }
                )
    except Exception:
        pass
    return articles


def puzzle_items():
    return [
        {
            "title": "The New York Times - Wordle Daily Challenge",
            "description": "Play today's official NYT Wordle puzzle and test your 5-letter word decoding skills.",
            "category": "Puzzles",
            "source": "The New York Times",
            "published": "Daily",
            "link": "https://www.nytimes.com/games/wordle/index.html",
        },
        {
            "title": "The Guardian - Daily Crossword Hub",
            "description": "Access quick, cryptic, and prize crosswords directly from major UK publishers.",
            "category": "Puzzles",
            "source": "The Guardian",
            "published": "Daily",
            "link": "https://www.theguardian.com/crosswords",
        },
        {
            "title": "The Independent - Daily Crosswords & Sudoku",
            "description": "Enjoy interactive daily crosswords and number puzzles from UK journalism.",
            "category": "Puzzles",
            "source": "The Independent",
            "published": "Daily",
            "link": "https://www.independent.co.uk/extras/puzzles",
        },
        {
            "title": "The New York Times - Mini Crossword",
            "description": "A quick and snappy crossword puzzle updated every morning.",
            "category": "Puzzles",
            "source": "The New York Times",
            "published": "Daily",
            "link": "https://www.nytimes.com/crosswords/game/mini",
        },
    ]


def fetch_fresh_news():
    """Fetch current multi-source news, Guardian API coverage and puzzles."""
    from news_freshness import fetch_multi_source_news

    all_articles = fetch_multi_source_news(load_custom_sources())
    for category in ("World", "Technology", "Business", "Science", "UK", "Sport"):
        all_articles.extend(fetch_guardian_articles(category))
    all_articles.extend(puzzle_items())

    # Apply the same football classification to RSS and API/Guardian stories.
    from news_freshness import classify_sport_focus

    for article in all_articles:
        if str(article.get("category") or "").strip().lower() == "sport":
            article["sport_focus"] = classify_sport_focus(
                article.get("title", ""),
                article.get("description", ""),
                article.get("sport_focus", ""),
            )

    # Keep the deterministic freshness ordering supplied by the feed layer.
    # Guardian/API and puzzle items are appended afterwards and therefore do
    # not displace current RSS reporting.
    news_articles = deduplicate_articles(all_articles)
    enriched = enrich_articles(news_articles)
    enriched.sort(key=lambda item: float(item.get("published_ts") or 0), reverse=True)
    return enriched


def refresh_news():
    articles = fetch_fresh_news()
    with _news_lock:
        _news_cache["articles"] = articles
        _news_cache["last_updated"] = time.time()
    return articles


def _cron_authorized() -> bool:
    """Validate the shared cron token without exposing it in normal responses."""
    expected = os.environ.get("KAIVOR_CRON_TOKEN", "").strip()
    if not expected:
        return False
    supplied = request.headers.get("Authorization", "").strip()
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    if not supplied:
        supplied = request.args.get("token", "").strip()
    return bool(supplied) and supplied == expected


def _background_startup():
    # Load local secrets/configuration at startup, but do not perform a
    # competing news refresh. Cloud news refreshes are owned by cron-job.org.
    try:
        load_persisted_secrets()
    except Exception:
        pass
    # Finance refresh is intentionally not started automatically here.
    # Keep finance fetching available to the API without creating a
    # competing long-lived network worker in the News service.


def _startup():
    # Do not block Gunicorn/Render startup on external RSS/API calls.
    threading.Thread(target=_background_startup, daemon=True, name="kaivor-startup").start()


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory("static", "manifest.webmanifest")


@app.route("/service-worker.js")
def service_worker():
    response = send_from_directory("static", "service-worker.js")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/icons/<path:filename>")
def pwa_icon(filename):
    return send_from_directory("static/icons", filename)


@app.route("/api/health", methods=["GET"])
def api_health():
    with _news_lock:
        news_last = float(_news_cache.get("last_updated") or 0)
        news_count = len(_news_cache.get("articles") or [])
    with _cache_lock:
        finance_last = float(_finance_cache.get("last_updated") or 0)
    now = time.time()
    return jsonify({
        "success": True,
        "status": "ok",
        "service": "kaivor-news",
        "version": "FP018.2",
        "news_count": news_count,
        "news_last_updated": news_last,
        "news_age_seconds": round(now - news_last, 1) if news_last else None,
        "finance_last_updated": finance_last,
        "finance_age_seconds": round(now - finance_last, 1) if finance_last else None,
        "cron_configured": bool(os.environ.get("KAIVOR_CRON_TOKEN", "").strip()),
        "cron_refresh_running": bool(_cron_refresh_state["running"]),
        "cron_refresh_last_completed": _cron_refresh_state["last_completed"],
        "cron_refresh_last_count": _cron_refresh_state["last_count"],
        "cron_refresh_last_error": _cron_refresh_state["last_error"],
        "time": datetime.now(timezone.utc).isoformat(),
    })


def _cron_refresh_worker() -> None:
    print("CRON WORKER: starting refresh", flush=True)
    try:
        started = time.time()
        print("CRON WORKER: calling refresh_news()", flush=True)
        articles = refresh_news()
        elapsed = round(time.time() - started, 2)
        print(f"CRON WORKER: refresh_news() completed in {elapsed}s with {len(articles)} articles", flush=True)
        with _cron_refresh_lock:
            _cron_refresh_state["last_completed"] = time.time()
            _cron_refresh_state["last_count"] = len(articles)
            _cron_refresh_state["last_error"] = ""
    except Exception as exc:
        print(f"CRON WORKER: ERROR {type(exc).__name__}: {exc}", flush=True)
        with _cron_refresh_lock:
            _cron_refresh_state["last_completed"] = time.time()
            _cron_refresh_state["last_count"] = 0
            _cron_refresh_state["last_error"] = type(exc).__name__
    finally:
        print("CRON WORKER: finished", flush=True)
        with _cron_refresh_lock:
            _cron_refresh_state["running"] = False


@app.route("/api/cron/refresh", methods=["GET", "POST"])
def api_cron_refresh():
    if not _cron_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    with _cron_refresh_lock:
        if _cron_refresh_state["running"]:
            return jsonify({
                "success": True,
                "status": "already_running",
                "message": "News refresh is already running.",
            }), 202

        _cron_refresh_state["running"] = True
        _cron_refresh_state["started_at"] = time.time()
        _cron_refresh_state["last_error"] = ""

    try:
        threading.Thread(
            target=_cron_refresh_worker,
            daemon=True,
            name="kaivor-cron-refresh",
        ).start()
    except Exception as exc:
        with _cron_refresh_lock:
            _cron_refresh_state["running"] = False
            _cron_refresh_state["last_error"] = type(exc).__name__

        return jsonify({
            "success": False,
            "error": "Could not start refresh",
        }), 500

    return jsonify({
        "success": True,
        "status": "started",
        "message": "News refresh started in background.",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }), 202


@app.route("/")
def index():
    with _cache_lock:
        market_data = _finance_cache.get(
            "data",
            {
                "gold": "2,650.00",
                "bitcoin": "64,200.00",
                "weather": "15°C",
                "SP500": "5,750.00",
                "Brent_Oil": "75.00",
                "GBP_USD": "1.33",
                "GBP_EUR": "1.19",
                "EUR_USD": "1.08",
            },
        )
    with _news_lock:
        articles = list(_news_cache.get("articles", []))
    saved_ids = {item["id"] for item in load_saved_articles()}
    return render_template("index.html", market=market_data, articles=articles, saved_ids=saved_ids)


@app.route("/api/ticker", methods=["GET"])
def api_ticker():
    with _cache_lock:
        data = dict(_finance_cache.get("data", {}))
        last_updated = float(_finance_cache.get("last_updated") or 0)
    with _finance_refresh_lock:
        state = dict(_finance_refresh_state)
    return jsonify({
        "success": True,
        "ticker": data,
        "last_updated": last_updated,
        "age_seconds": round(max(0, time.time() - last_updated), 1) if last_updated else None,
        "refresh": state,
    })


@app.route("/api/finance/refresh", methods=["POST"])
def api_finance_refresh():
    with _finance_refresh_lock:
        if _finance_refresh_state["running"]:
            return jsonify({"success": True, "status": "running", "message": "Market refresh is already running."}), 202
        _finance_refresh_state["running"] = True
        _finance_refresh_state["started_at"] = time.time()
        _finance_refresh_state["last_error"] = ""
        _finance_refresh_state["last_updated_keys"] = []
    try:
        threading.Thread(target=_finance_refresh_worker, daemon=True, name="kaivor-finance-refresh").start()
    except Exception:
        with _finance_refresh_lock:
            _finance_refresh_state["running"] = False
        return jsonify({"success": False, "status": "error", "message": "Could not start market refresh."}), 500
    return jsonify({"success": True, "status": "started", "message": "Market refresh started."}), 202


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    articles = refresh_news()
    return jsonify({"success": True, "count": len(articles)})


@app.route("/api/sources", methods=["GET"])
def api_sources():
    return jsonify({"success": True, "sources": build_rss_sources()})


@app.route("/api/add_feed", methods=["POST"])
def api_add_feed():
    data = request.json or {}
    name = str(data.get("name", "")).strip()
    url_input = str(data.get("url", "")).strip()
    if not name or not url_input:
        return jsonify({"success": False, "error": "Both source name/category and URL/publication are required."}), 400

    target_url = url_input
    if not url_input.lower().startswith(("http://", "https://")):
        found_url = find_rss_via_brave(url_input)
        if found_url:
            target_url = found_url
    if not target_url.lower().startswith(("http://", "https://")):
        return jsonify({"success": False, "error": "Could not resolve a valid HTTP/HTTPS feed URL."}), 400

    custom = load_custom_sources()
    custom.setdefault(name, [])
    if target_url not in custom[name]:
        custom[name].append(target_url)
    save_custom_sources(custom)
    refresh_news()
    return jsonify({"success": True, "resolved_url": target_url})


@app.route("/api/set_key", methods=["POST"])
def api_set_key():
    data = request.json or {}
    key_type = str(data.get("type", "")).strip().lower()
    api_key = str(data.get("api_key", "")).strip()
    if key_type not in {"openrouter", "openai", "guardian", "brave"} or not api_key:
        return jsonify({"success": False, "error": "Unsupported key type or empty API key."}), 400

    if not save_secret(key_type, api_key):
        return jsonify({"success": False}), 400
    os.environ[
        {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "guardian": "GUARDIAN_API_KEY",
            "brave": "BRAVE_API_KEY",
        }[key_type]
    ] = api_key
    refresh_news()
    return jsonify({"success": True, "persisted": True})


@app.route("/api/saved", methods=["GET"])
def api_saved():
    saved = load_saved_articles()
    return jsonify({"success": True, "articles": saved, "count": len(saved)})


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.json or {}
    article = data.get("article")
    if not isinstance(article, dict):
        return jsonify({"success": False, "error": "Article payload is required."}), 400
    saved = save_article(article)
    return jsonify({"success": True, "article": saved, "saved": True})


@app.route("/api/save/<article_id_value>", methods=["DELETE"])
def api_remove_saved(article_id_value):
    removed = remove_saved_article(article_id_value)
    return jsonify({"success": removed, "saved": False})


@app.route("/api/relevance_profile", methods=["GET", "PUT"])
def api_relevance_profile():
    if request.method == "GET":
        return jsonify({"success": True, "profile": load_profile()})

    data = request.json or {}
    profile = data.get("profile") if isinstance(data, dict) else None
    if not isinstance(profile, dict):
        return jsonify({"success": False, "error": "Profile object is required."}), 400
    saved = save_profile(profile)
    with _news_lock:
        current = list(_news_cache.get("articles", []))
    if current:
        from story_intelligence import enrich_articles as _enrich_articles
        refreshed = _enrich_articles(current)
        with _news_lock:
            _news_cache["articles"] = refreshed
    return jsonify({"success": True, "profile": saved})


@app.route("/api/story_timeline", methods=["POST"])
def api_story_timeline():
    data = request.json or {}
    article = data.get("article") or {}
    if not isinstance(article, dict) or not article.get("title"):
        return jsonify({"success": False, "error": "Article context is required."}), 400

    cluster_id = str(article.get("cluster_id") or "")
    members = []
    if cluster_id:
        with _news_lock:
            members = [
                item for item in _news_cache.get("articles", [])
                if item.get("cluster_id") == cluster_id
            ][:12]

    if not members:
        members = [article]

    timeline = build_story_timeline(members)
    return jsonify(
        {
            "success": True,
            "timeline": timeline,
            "evidence_note": "Timeline is based only on reports currently held by Kaivor for this story.",
        }
    )


@app.route("/api/story_intelligence", methods=["POST"])
def api_story_intelligence():
    data = request.json or {}
    article = data.get("article") or {}
    if not isinstance(article, dict) or not article.get("title"):
        return jsonify({"success": False, "error": "Article context is required."}), 400

    article = dict(article)
    cluster_id = str(article.get("cluster_id") or "")
    if cluster_id:
        with _news_lock:
            related = [
                item for item in _news_cache.get("articles", [])
                if item.get("cluster_id") == cluster_id and item.get("id") != article.get("id")
            ][:8]
        article["related_articles"] = related

    source_count = int(article.get("source_count") or article.get("independent_source_count") or 1)
    report_count = int(article.get("report_count") or max(1, int(article.get("related_count") or 0) + 1))
    repeated_same_source = int(article.get("repeated_same_source_reports") or 0)
    source_groups = article.get("story_sources") or []
    members = [article] + [item for item in article.get("related_articles") or [] if item.get("id") != article.get("id")]
    importance_model = build_importance_model(members, story_status=str(article.get("story_status") or ""))
    importance = importance_model["importance"]
    confidence_assessment = importance_model["confidence_assessment"]
    relevance = calculate_personal_relevance(article, load_profile())
    deterministic = (
        f"WHAT WE KNOW\n{article.get('what_we_know_hint') or 'Kaivor has limited evidence for this report.'}\n\n"
        f"WHY IT MATTERS\n{article.get('impact_hint') or article.get('why_matters_hint') or 'The significance depends on what is confirmed next.'}\n\n"
        f"IMPORTANCE\n{importance['label']} ({importance['score']}/100)\n{' '.join(importance['reasons'])}\n\n"
        f"CONFIDENCE\n{confidence_assessment['label']} ({confidence_assessment['score']}/100)\n{' '.join(confidence_assessment['reasons'])}\n\n"
        f"PERSONAL RELEVANCE\n{relevance['label']} ({relevance['score']}/100)\n{' '.join(relevance['reasons'])}\n\n"
        f"EVIDENCE STATUS\n{article.get('evidence_status') or 'Single-source'}\n"
        f"{evidence_sentence({
            'source_count': source_count,
            'report_count': report_count,
            'repeated_same_source_reports': repeated_same_source,
            'story_sources': source_groups,
        })}"
        + "\n\n"
        f"WHAT REMAINS UNCERTAIN\n{article.get('uncertainty_hint') or 'Further primary evidence or independent reporting could change the picture.'}"
    )

    context = [
        f"Title: {article.get('title', '')}",
        f"Source: {article.get('source', '')}",
        f"Category: {article.get('category', '')}",
        f"Published: {article.get('published', '')}",
        f"Summary: {article.get('description', '')}",
        f"Evidence status: {article.get('evidence_status', 'Single-source')}",
        f"Independent source-group count: {source_count}",
        f"Source groups: {', '.join(source_groups)}",
        f"Related report count: {report_count}",
        f"Repeated same-source reports: {repeated_same_source}",
        f"Importance: {importance['label']} ({importance['score']}/100)",
        f"Importance reasons: {' '.join(importance['reasons'])}",
        f"Confidence: {confidence_assessment['label']} ({confidence_assessment['score']}/100)",
        f"Confidence reasons: {' '.join(confidence_assessment['reasons'])}",
        f"Personal relevance: {relevance['label']} ({relevance['score']}/100)",
        f"Personal relevance reasons: {' '.join(relevance['reasons'])}",
    ]
    for item in article.get("related_articles") or []:
        context.append(
            f"Related report | source={item.get('source', '')} | title={item.get('title', '')} | summary={item.get('description', '')}"
        )

    system = (
        "You are Kaivor's evidence-first news intelligence analyst. Use only the supplied article and related-report context. "
        "Do not invent facts, motives, numbers, casualties, damage, locations, outcomes or causal links. "
        "Return exactly seven short sections: WHAT WE KNOW, WHY IT MATTERS, IMPORTANCE, CONFIDENCE, EVIDENCE STATUS, WHAT REMAINS UNCERTAIN, SOURCES. "
        "Use concrete story-specific details from the supplied text. Never use generic filler such as 'the significance should be assessed against wider context'. "
        "Distinguish multiple reports from multiple independent sources. Same-source reports are not independent corroboration. "
        "If evidence is thin, explicitly say that. Use the supplied deterministic importance and confidence assessments; do not invent scores or upgrade confidence. Keep the answer concise and factual.\n\n"
        + "\n".join(context)
    )

    providers = []
    if os.environ.get("OPENROUTER_API_KEY"):
        providers.append(("openrouter", "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"], "deepseek/deepseek-chat"))
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "https://api.openai.com/v1/chat/completions", os.environ["OPENAI_API_KEY"], "gpt-4o-mini"))

    for provider, url, key, model in providers:
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": "Produce the seven-section intelligence assessment now."},
                ],
                "temperature": 0.1,
            }
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if len(content) > 80:
                    return jsonify({"success": True, "analysis": content, "provider": provider, "evidence": {"source_count": source_count, "report_count": report_count}})
        except Exception:
            continue

    return jsonify({"success": True, "fallback": True, "analysis": deterministic, "evidence": {"source_count": source_count, "report_count": report_count}})


@app.route("/api/why_matters", methods=["POST"])
def api_why_matters():
    data = request.json or {}
    article = data.get("article") or {}
    if not isinstance(article, dict) or not article.get("title"):
        return jsonify({"success": False, "error": "Article context is required."}), 400

    category = str(article.get("category") or "News").strip()
    title = str(article.get("title") or "").strip()
    hint = str(article.get("why_matters_hint") or article.get("impact_hint") or "").strip()
    if hint and not hint.lower().startswith("the immediate significance depends"):
        return jsonify({"success": True, "why": hint, "source": "deterministic"})

    templates = {
        "World": "This matters because developments like this can affect people, governments and international stability. The wider significance depends on what is confirmed next.",
        "UK": "This matters because it could affect people, public services or government decisions in the UK. The practical impact depends on what happens next.",
        "Technology": "This matters because it could affect how technology is developed, used or regulated. Its longer-term importance depends on adoption and independent verification.",
        "Business": "This matters because it could affect companies, consumers, employment or markets. The scale of the impact depends on what happens next.",
        "Science": "This matters because it may add to our understanding of an important scientific or health issue. Its significance depends on the strength of the evidence and further research.",
        "Sport": "This matters because it could affect results, qualification, selection, form or the wider competition picture.",
    }
    why = templates.get(category, "This matters because it represents a current development worth monitoring. Its wider significance depends on what is confirmed next.")
    return jsonify({"success": True, "why": why, "source": "deterministic", "title": title})


@app.route("/api/ai_brief", methods=["POST"])
def api_ai_brief():
    data = request.json or {}
    article_title = data.get("title", "")
    article_desc = data.get("description", "")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Provide a short 3-bullet summary: 1) What happened, 2) Why it matters, 3) Next outlook. Do not invent facts."},
                    {"role": "user", "content": f"Title: {article_title}\nSummary: {article_desc}"},
                ],
                "temperature": 0.3,
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return jsonify({"success": True, "brief": response.json()["choices"][0]["message"]["content"]})
        except Exception:
            pass

    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Provide a short 3-bullet summary: 1) What happened, 2) Why it matters, 3) Next outlook. Do not invent facts."},
                    {"role": "user", "content": f"Title: {article_title}\nSummary: {article_desc}"},
                ],
                "temperature": 0.3,
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return jsonify({"success": True, "brief": response.json()["choices"][0]["message"]["content"]})
        except Exception:
            pass

    fallback_brief = (
        f"• What happened: Key updates regarding '{article_title}'.\n"
        "• Significance: Review the source coverage for the verified context.\n"
        "• Outlook: Continued monitoring advised."
    )
    return jsonify({"success": True, "brief": fallback_brief, "fallback": True})


@app.route("/api/ask_ai", methods=["POST"])
def api_ask_ai():
    data = request.json or {}
    question = str(data.get("question") or "What are the implications?").strip()
    article_title = str(data.get("title") or "").strip()
    article_desc = str(data.get("description") or "").strip()
    providers = []
    if os.environ.get("OPENROUTER_API_KEY"):
        providers.append(("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"], "deepseek/deepseek-chat"))
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("OpenAI", "https://api.openai.com/v1/chat/completions", os.environ["OPENAI_API_KEY"], "gpt-4o-mini"))

    if not providers:
        return jsonify({"success": False, "error": "No AI provider is configured. Add an OpenRouter or OpenAI API key in Sources & API Settings."}), 503

    errors = []
    for provider, url, key, model in providers:
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are Kaivor News. Answer the user's question about the supplied article concisely and professionally. Use only the supplied article context. Clearly distinguish facts from uncertainty. Do not invent facts."},
                    {"role": "user", "content": f"Article title: {article_title}\nArticle summary: {article_desc}\n\nQuestion: {question}"},
                ],
                "temperature": 0.2,
            }
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return jsonify({"success": True, "answer": content, "provider": provider})
                errors.append(f"{provider}: empty response")
            else:
                try:
                    detail = response.json().get("error", {}).get("message", "")
                except Exception:
                    detail = ""
                errors.append(f"{provider}: HTTP {response.status_code}" + (f" — {detail[:180]}" if detail else ""))
        except requests.RequestException as exc:
            errors.append(f"{provider}: connection error ({type(exc).__name__})")
        except Exception:
            errors.append(f"{provider}: unexpected provider response")

    return jsonify({
        "success": False,
        "error": "AI could not answer this question right now.",
        "details": " | ".join(errors),
    }), 503


_startup()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
