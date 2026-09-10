from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory

import feedparser
import requests
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# Set your DeepSeek API key (or configure it securely in your Render Environment Variables)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-a4c7cb47c96e46a58c4787116202d031")

sources = [
    # UK News
    {"name": "BBC UK News", "url": "http://feeds.bbci.co.uk/news/uk/rss.xml", "category": "UK"},
    {"name": "The Guardian UK", "url": "https://www.theguardian.com/uk-news/rss", "category": "UK"},
    {"name": "Sky News UK", "url": "https://news.sky.com/feeds/rss/uk.xml", "category": "UK"},
    {"name": "The Telegraph", "url": "https://www.telegraph.co.uk/news/rss.xml", "category": "UK"},
    # World
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "category": "World"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "category": "World"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best", "category": "World"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "World"},
    {"name": "CNN World", "url": "http://rss.cnn.com/rss/edition_world.rss", "category": "World"},
    # Tech
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "category": "Tech"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Tech"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "Tech"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "Tech"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Tech"},
    # AI
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "AI"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "AI"},
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
    {"name": "Blabbermouth", "url": "https://www.blabbermouth.net/feed", "category": "Music"},
    # Android
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/", "category": "Android"},
    {"name": "9to5Google", "url": "https://9to5google.com/feed/", "category": "Android"},
    # Business
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "category": "Business"},
    {"name": "Financial Times", "url": "https://www.ft.com/?format=rss", "category": "Business"},
]

def extract_image(entry):
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media:
                return media['url']
    if 'media_thumbnail' in entry:
        if 'url' in entry.media_thumbnail[0]:
            return entry.media_thumbnail[0]['url']
            
    summary = entry.get("summary", "") or entry.get("description", "")
    match = re.search(r'src="([^"]+)"', summary)
    if match:
        return match.group(1)
        
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=300&q=80"

def fetch_single_source(source):
    """Fetches a single feed with a strict 1-second timeout to prevent any hanging."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(source['url'], headers=headers, timeout=1.0)
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

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    
@app.route('/brief', methods=['POST'])
def brief_article():
    data = request.get_json()
    article_title = data.get('title', '')
    
    if not article_title:
        return jsonify({"summary": "No article title provided."})

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a sharp, concise news summarizer. Provide a 3-sentence summary of the news topic."},
                {"role": "user", "content": f"Summarize this news headline/topic concisely: {article_title}"}
            ],
            "stream": False
        }
        response = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            result = response.json()
            summary = result['choices'][0]['message']['content']
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
        "S&P 500": 5850.00,
        "NASDAQ": 18300.00,
        "FTSE 100": 8250.00,
        "Bitcoin": 92500.00,
        "Gold": 2700.50
    }

    news_by_category = {}
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_single_source, source) for source in sources]
        for future in as_completed(futures):
            try:
                result = future.result(timeout=1.5)
                if result:
                    cat, name, articles = result
                    if cat not in news_by_category:
                        news_by_category[cat] = {}
                    news_by_category[cat][name] = articles
            except Exception:
                pass

    news_by_category["Puzzles"] = {
        "Newspaper Crosswords & Daily Games": [
            {
                "title": "Wordle - Daily Word Puzzle (New York Times)",
                "link": "https://www.nytimes.com/games/wordle/index.html",
                "image": "https://images.unsplash.com/photo-1529699211952-734e80c4d42b?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "The Mini Crossword - New York Times",
                "link": "https://www.nytimes.com/crosswords/game/mini",
                "image": "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Connections - New York Times Word Grouping",
                "link": "https://www.nytimes.com/games/connections",
                "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Spelling Bee - New York Times Letter Puzzle",
                "link": "https://www.nytimes.com/puzzles/spelling-bee",
                "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Los Angeles Times Daily Crossword",
                "link": "https://www.latimes.com/games/crossword",
                "image": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?auto=format&fit=crop&w=300&q=80"
            }
        ]
    }

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data, sources=sources)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
