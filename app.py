from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import feedparser
import requests
import re
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

sources = [
    # UK News
    {"name": "BBC News UK", "url": "https://feeds.bbci.co.uk/news/uk/rss.xml", "category": "UK"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/uk-news/rss", "category": "UK"},
    {"name": "Sky News UK", "url": "https://news.sky.com/feeds/rss/uk.xml", "category": "UK"},
    # World
    {"name": "BBC News World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "World"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best", "category": "World"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "World"},
    # Tech
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Tech"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "Tech"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "Tech"},
    # AI
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "AI"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/category/ai/feed/", "category": "AI"},
    # Sport
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "category": "Sport"},
    {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "category": "Sport"},
    # Music
    {"name": "Billboard", "url": "https://www.billboard.com/feed/", "category": "Music"},
    {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/music-news/feed/", "category": "Music"},
    # Android
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/", "category": "Android"},
    {"name": "9to5Google", "url": "https://9to5google.com/feed/", "category": "Android"},
    # Business
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "category": "Business"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss", "category": "Business"}
]

cache = {
    "news": {},
    "market": {
        "GBP/USD": "Loading...",
        "EUR/USD": "Loading...",
        "USD/JPY": "Loading...",
        "Bitcoin": "Loading..."
    },
    "last_updated": 0
}
cache_lock = threading.Lock()

CATEGORY_FALLBACKS = {
    "UK": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=600&auto=format&fit=crop&q=60",
    "World": "https://images.unsplash.com/photo-1521295121783-8a321d5d1ad2?w=600&auto=format&fit=crop&q=60",
    "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=60",
    "AI": "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=600&auto=format&fit=crop&q=60",
    "Sport": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&auto=format&fit=crop&q=60",
    "Music": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=60",
    "Android": "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?w=600&auto=format&fit=crop&q=60",
    "Business": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&auto=format&fit=crop&q=60"
}

def extract_image(entry, category="Tech"):
    # 1. Check media_content
    if "media_content" in entry:
        for media in entry.media_content:
            if isinstance(media, dict) and 'url' in media:
                return media['url']
            elif hasattr(media, 'get'):
                url = media.get('url')
                if url:
                    return url

    # 2. Check media_thumbnail
    if "media_thumbnail" in entry:
        thumbs = entry.media_thumbnail
        if isinstance(thumbs, list) and len(thumbs) > 0:
            if isinstance(thumbs[0], dict) and 'url' in thumbs[0]:
                return thumbs[0]['url']
            elif hasattr(thumbs[0], 'get'):
                return thumbs[0].get('url')
        elif isinstance(thumbs, dict) and 'url' in thumbs:
            return thumbs.get('url')

    # 3. Check enclosures or links for image types/urls
    for key in ["enclosures", "links"]:
        if key in entry:
            for item in entry[key]:
                href = item.get("href") or item.get("url")
                if href and (any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or item.get("type", "").startswith("image/")):
                    return href

    # 4. Deep search all string fields (summary, description, content, etc.) for any image URL or HTML img tag
    for field in ["content", "summary", "description", "subtitle", "title"]:
        if field in entry:
            val = entry.get(field, "")
            if isinstance(val, list):
                val = "".join([str(c.get("value", "")) for c in val])
            # Search for HTML img src
            match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', str(val), re.IGNORECASE)
            if match:
                return match.group(1)
            # Search for raw image URL ending in extension inside text
            url_match = re.search(r'(https?://[^\s<>"]+?\.(?:jpg|jpeg|png|webp))', str(val), re.IGNORECASE)
            if url_match:
                return url_match.group(1)

    return CATEGORY_FALLBACKS.get(category, "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=600&auto=format&fit=crop&q=60")

def parse_entry_time(entry):
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        return time.mktime(time_struct)
    return time.time()

def fetch_single_source(source):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(source['url'], headers=headers, timeout=3.0)
        if response.status_code == 200:
            parsed = feedparser.parse(response.text)
            sorted_entries = sorted(parsed.entries, key=parse_entry_time, reverse=True)
            
            articles = []
            for entry in sorted_entries[:4]:
                pub_time = parse_entry_time(entry)
                time_ago = int((time.time() - pub_time) / 60)
                if time_ago < 60:
                    time_str = f"{max(time_ago, 1)}m ago"
                elif time_ago < 1440:
                    time_str = f"{int(time_ago / 60)}h ago"
                else:
                    time_str = f"{int(time_ago / 1440)}d ago"

                articles.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", "#"),
                    "image": extract_image(entry, source['category']),
                    "time": time_str
                })
            if articles:
                return source['category'], source['name'], articles
    except Exception:
        pass
    return None

def fetch_live_market_data():
    market = {
        "GBP/USD": "1.28",
        "EUR/USD": "1.08",
        "USD/JPY": "155.20",
        "Bitcoin": "$92,500"
    }
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3.0)
        if res.status_code == 200:
            rates = res.json().get("rates", {})
            if "GBP" in rates:
                market["GBP/USD"] = f"{round(1 / rates['GBP'], 4)}"
            if "EUR" in rates:
                market["EUR/USD"] = f"{round(1 / rates['EUR'], 4)}"
            if "JPY" in rates:
                market["USD/JPY"] = f"{round(rates['JPY'], 2)}"
    except Exception:
        pass

    try:
        btc_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=3.0)
        if btc_res.status_code == 200:
            btc_price = btc_res.json().get("bitcoin", {}).get("usd")
            if btc_price:
                market["Bitcoin"] = f"${int(btc_price):,}"
    except Exception:
        pass

    return market

def refresh_feed_cache():
    news_by_category = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_single_source, source) for source in sources]
        
        for future in as_completed(futures):
            try:
                result = future.result(timeout=3.5)
                if result:
                    cat, name, articles = result
                    if cat not in news_by_category:
                        news_by_category[cat] = {}
                    news_by_category[cat][name] = articles
            except Exception:
                pass

    news_by_category['Fun / Puzzles'] = {
        "Daily Games & Puzzles": [
            {"title": "Wordle - Daily Word Puzzle (New York Times)", "link": "https://www.nytimes.com/games/wordle/index.html", "image": "https://images.unsplash.com/photo-1529653719697-40f4e9ff761b?w=600&auto=format&fit=crop&q=60", "time": "Live"},
            {"title": "The Mini Crossword - New York Times", "link": "https://www.nytimes.com/crosswords/game/mini", "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=600&auto=format&fit=crop&q=60", "time": "Live"},
            {"title": "Connections - New York Times Nerd Grouping", "link": "https://www.nytimes.com/games/connections", "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60", "time": "Live"}
        ]
    }

    live_market = fetch_live_market_data()

    with cache_lock:
        cache["news"] = news_by_category
        cache["market"] = live_market
        cache["last_updated"] = time.time()

refresh_feed_cache()

def background_worker():
    while True:
        time.sleep(600)
        refresh_feed_cache()

threading.Thread(target=background_worker, daemon=True).start()

@app.route('/health')
def health_check():
    return "OK", 200

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json', mimetype='application/json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')

@app.route('/brief', methods=['POST'])
def brief():
    data = request.get_json()
    article_title = data.get('title', '')
    if not article_title:
        return jsonify({"summary": "No article title provided."})
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://kaivor-news.onrender.com",
        "X-Title": "Kaivor News"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a sharp, concise news summarizer. Provide a 1-sentence summary of this news headline/topic concisely."},
            {"role": "user", "content": f"Summarize this news headline/topic concisely: {article_title}"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            return jsonify({"summary": summary})
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        
    return jsonify({"summary": "Could not generate summary at this time."})

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        preset_url = request.form.get('preset_url')
        feed_category = request.form.get('feed_category', 'Tech')
        if preset_url:
            feed_name = "Custom Feed"
            for s in sources:
                if s['url'] == preset_url:
                    feed_name = s['name']
            if not any(s['url'] == preset_url for s in sources):
                sources.append({"name": feed_name, "url": preset_url, "category": feed_category})
            refresh_feed_cache()
        return redirect(url_for('index'))

    with cache_lock:
        news_by_category = cache["news"]
        market_data = cache["market"]

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data, sources=sources)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
