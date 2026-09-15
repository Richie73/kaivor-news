import os
import time
import threading
import feedparser
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed

# Automatically find templates whether they are in 'templates' or 'app/templates'
template_dir = 'app/templates' if os.path.exists('app/templates') else 'templates'
app = Flask(__name__, template_folder=template_dir)

# Safe fallback global cache initialization to prevent KeyErrors on startup
cache_lock = threading.Lock()
cache = {
    "news": {},
    "market": {}
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

sources = [
    # UK News
    {"name": "BBC News UK", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/uk/rss"},
    {"name": "Sky News UK", "url": "https://news.sky.com/feed/rss"},
    # World
    {"name": "BBC News World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best"}
]

def fetch_single_feed(source):
    try:
        parsed = feedparser.parse(source['url'])
        entries = []
        for entry in parsed.entries[:5]:
            entries.append({
                "title": getattr(entry, 'title', 'No Title'),
                "link": getattr(entry, 'link', '#'),
                "published": getattr(entry, 'published', 'Recent'),
                "summary": getattr(entry, 'summary', '')
            })
        return source['name'], entries
    except Exception as e:
        print(f"Error fetching feed {source['name']}: {e}")
        return source['name'], []

def refresh_feed_cache():
    news_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_source = {executor.submit(fetch_single_feed, src): src for src in sources}
        for future in as_completed(future_to_source):
            name, entries = future.result()
            if entries:
                news_data[name] = entries
    
    with cache_lock:
        cache["news"] = news_data
        cache["market"] = {"Status": "Live Feed Active"}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        preset_url = request.form.get('preset_url')
        if preset_url:
            feed_name = "Custom Feed"
            for s in sources:
                if s['url'] == preset_url:
                    feed_name = s['name']
            if not any(s['url'] == preset_url for s in sources):
                sources.append({"name": feed_name, "url": preset_url})
            refresh_feed_cache()
            return redirect(url_for('index'))

    with cache_lock:
        news_by_category = cache.get("news", {})
        market_data = cache.get("market", {})
        sources_list = sources

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data, sources=sources_list)

@app.route('/health')
def health():
    return "OK", 200

# Automatically spin up background thread to pre-load feeds on startup
threading.Thread(target=refresh_feed_cache, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
        
