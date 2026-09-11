from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import feedparser
import requests
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_connected

app = Flask(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")

sources = [
    # UK News
    {"name": "BBC News UK", "url": "https://feeds.bbci.co.uk/news/uk/rss.xml", "category": "UK"},
    {"name": "The Guardian UK", "url": "https://www.theguardian.com/uk-news/rss", "category": "UK"},
    {"name": "Sky News UK", "url": "https://news.sky.com/feeds/rss/uk.xml", "category": "UK"},
    {"name": "The Telegraph", "url": "https://www.telegraph.co.uk/news-and-current-affairs/rss.xml", "category": "UK"},
    # World
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "World"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "category": "World"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best", "category": "World"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "World"},
    {"name": "CNN World", "url": "http://rss.cnn.com/rss/edition_world.rss", "category": "World"},
    # Tech
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Tech"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "Tech"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "Tech"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Tech"},
    # AI
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "AI"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/category/ai/feed/", "category": "AI"},
    # Sport
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "category": "Sport"},
    {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "category": "Sport"},
    {"name": "Sky Sports", "url": "https://www.skysports.com/core/rss/12040", "category": "Sport"},
    # Music
    {"name": "Pitchfork", "url": "https://pitchfork.com/feed/feed-news/rss", "category": "Music"},
    {"name": "Billboard", "url": "https://www.billboard.com/feed/", "category": "Music"},
    {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/music-news/feed/", "category": "Music"},
    {"name": "NME", "url": "https://www.nme.com/feed", "category": "Music"},
    {"name": "Louder", "url": "https://www.loudersound.com/feeds.xml", "category": "Music"},
    {"name": "Blabbermouth", "url": "https://blabbermouth.net/feed/", "category": "Music"},
    # Android
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/", "category": "Android"},
    {"name": "9to5Google", "url": "https://9to5google.com/feed/", "category": "Android"},
    # Business
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "category": "Business"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss", "category": "Business"}
]

def extract_image(entry):
    if "media_content" in entry:
        for media in entry.media_content:
            if isinstance(media, dict) and 'url' in media:
                return media['url']
            elif hasattr(media, 'get'):
                url = media.get('url')
                if url:
                    return url
    
    if "media_thumbnail" in entry:
        thumbs = entry.media_thumbnail
        if isinstance(thumbs, list) and len(thumbs) > 0:
            if isinstance(thumbs[0], dict) and 'url' in thumbs[0]:
                return thumbs[0]['url']
            elif hasattr(thumbs[0], 'get'):
                return thumbs[0].get('url')
        elif isinstance(thumbs, dict) and 'url' in thumbs:
            return thumbs.get('url')

    if "enclosures" in entry:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href")

    content_blob = entry.get("summary", "") or entry.get("description", "") or entry.get("content", [{"value": ""}][0].get("value", ""))
    match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', content_blob, re.IGNORECASE)
    if match:
        return match.group(1)
        
    return "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=600&auto=format&fit=crop&q=60"

def fetch_single_source(source):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(source['url'], headers=headers, timeout=2.0)
        if response.status_code == 200:
            parsed = feedparser.parse(response.text)
            articles = []
            for entry in parsed.entries[:3]:
                articles.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", "#"),
                    "image": extract_image(entry)
                })
            if articles:
                return source['category'], source['name'], articles
    except Exception:
        pass
    return None

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
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a sharp, concise news summarizer. Provide a 1-sentence summary of this news headline/topic concisely."},
            {"role": "user", "content": f"Summarize this news headline/topic concisely: {article_title}"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            return jsonify({"summary": summary})
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        
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
                
        return redirect(url_for('index'))

    market_data = {
        "S&P 500": "5,840.00",
        "NASDAQ": "18,350.00",
        "FTSE 100": "8,240.00",
        "Bitcoin": "$92,500",
        "Gold": "$2,700.50"
    }

    news_by_category = {}

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_single_source, source): source for source in sources}
        for future in as_connected(futures):
            try:
                result = future.result(timeout=2.5)
                if result:
                    cat, name, articles = result
                    if cat not in news_by_category:
                        news_by_category[cat] = {}
                    news_by_category[cat][name] = articles
            except Exception:
                pass

    news_by_category['Fun / Puzzles'] = {
        "Newspaper Crosswords & Daily Games": [
            {
                "title": "Wordle - Daily Word Puzzle (New York Times)",
                "link": "https://www.nytimes.com/games/wordle/index.html",
                "image": "https://images.unsplash.com/photo-1529653719697-40f4e9ff761b?w=600&auto=format&fit=crop&q=60"
            },
            {
                "title": "The Mini Crossword - New York Times",
                "link": "https://www.nytimes.com/crosswords/game/mini",
                "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=600&auto=format&fit=crop&q=60"
            },
            {
                "title": "Connections - New York Times Nerd Grouping",
                "link": "https://www.nytimes.com/games/connections",
                "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60"
            },
            {
                "title": "Spelling Bee - New York Times Letter Puzzle",
                "link": "https://www.nytimes.com/puzzles/spelling-bee",
                "image": "https://www.nytimes.com/puzzles/spelling-bee",
                "image": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=600&auto=format&fit=crop&q=60"
            },
            {
                "title": "The Los Angeles Times Daily Crossword",
                "link": "https://www.latimes.com/games/crossword",
                "image": "https://images.unsplash.com/photo-1516962214119-7fd2adb58e78?w=600&auto=format&fit=crop&q=60"
            }
        ]
    }

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data, sources=sources)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
