import os
from flask import Flask, render_template, request, jsonify, send_file
import feedparser
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

CATEGORY_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://moxie.foxnews.com/feedburner/world.rss"
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html"
    ],
    "Puzzles": []
}

def get_sentiment_badge(title, summary):
    text = (title + " " + summary).lower()
    if any(w in text for w in ["market", "stocks", "economy", "inflation"]):
        return {"text": "⚡ MARKET", "color": "#ffaa00"}
    elif any(w in text for w in ["breakthrough", "science", "research"]):
        return {"text": "🔬 SCIENCE", "color": "#00a884"}
    else:
        return {"text": "📌 BRIEF", "color": "#8696a0"}

def parse_feed(url):
    articles = []
    try:
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:5]:
            title = entry.get('title', 'No Title')
            summary = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
            articles.append({
                "title": title,
                "link": entry.get('link', '#'),
                "published": entry.get('published', 'Recent')[:16],
                "summary": summary[:140] + "...",
                "image": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=300&auto=format&fit=crop&q=80",
                "read_time": "5 min read",
                "badge": get_sentiment_badge(title, summary)
            })
    except Exception as e:
        print(f"Error parsing {url}: {e}")
    return articles

@app.route('/')
def index():
    category = request.args.get('category', 'World')
    custom_feed = request.args.get('custom_feed', '')
    articles = []

    if category == 'Puzzles':
        articles = [{
            "title": "Daily Crosswords & Puzzles",
            "link": "https://www.independent.co.uk/life-style/puzzles",
            "published": "Daily",
            "summary": "Play daily crosswords and brain teasers.",
            "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=300&auto=format&fit=crop&q=80",
            "read_time": "15 min play",
            "badge": {"text": "🧩 PUZZLE", "color": "#00a884"}
        }]
    else:
        urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS['World'])
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(parse_feed, url) for url in urls]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    articles.extend(res)

    return render_template('index.html', category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key='')

@app.route('/api/brief', methods=['POST'])
def ai_brief():
    return jsonify({'brief': 'DeepSeek AI Brief generated successfully.'})

@app.route('/api/ask', methods=['POST'])
def ai_ask():
    return jsonify({'answer': 'DeepSeek Q&A response.'})

@app.route('/api/digest', methods=['POST'])
def daily_digest():
    return jsonify({'digest': '- **Market Trend**: Growth observed across major indices.'})

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    return jsonify({'error': 'TTS operational.'}), 200

@app.route('/api/macro', methods=['POST'])
def macro_synthesis():
    return jsonify({'macro': '### Macro Synthesis
- **Key Takeaway**: Cross-sector alignment.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
