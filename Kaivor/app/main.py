import os
import time
import threading
import feedparser
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from concurrent.futures import ThreadPoolExecutor, as_completed

# Absolute template path relative to this file
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "kaivor.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

class SavedArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    source = db.Column(db.String(100), nullable=True)

class CustomFeed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(400), unique=True, nullable=False)
    category = db.Column(db.String(50), default="Tech")

# Initialize database tables
with app.app_context():
    db.create_all()

# Default categories and feeds mapping
CATEGORY_SOURCES = {
    "World": [
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.rss"},
        {"name": "BBC News World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"}
    ],
    "Business": [
        {"name": "Financial Times", "url": "https://www.ft.com/?format=rss"},
        {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"}
    ],
    "Tech": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"}
    ],
    "UK": [
        {"name": "BBC News UK", "url": "https://feeds.bbci.co.uk/news/uk/rss.xml"},
        {"name": "The Guardian UK", "url": "https://www.theguardian.com/uk/rss"}
    ],
    "Sport": [
        {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml"}
    ],
    "Music": [
        {"name": "Pitchfork", "url": "https://pitchfork.com/feed/feed-news/rss"}
    ]
}

def calculate_read_time(summary):
    words = len(summary.split())
    minutes = max(1, words // 40)
    return f"{minutes} min read"

def fetch_feed_entries(feed_name, feed_url):
    try:
        parsed = feedparser.parse(feed_url)
        entries = []
        for entry in parsed.entries[:5]:
            summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
            entries.append({
                "title": getattr(entry, 'title', 'No Title'),
                "link": getattr(entry, 'link', '#'),
                "published": getattr(entry, 'published', 'Recent'),
                "summary": summary,
                "read_time": calculate_read_time(summary)
            })
        return feed_name, entries
    except Exception as e:
        print(f"Error fetching {feed_name}: {e}")
        return feed_name, []

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle adding custom feeds
        custom_url = request.form.get('url')
        category = request.form.get('category', 'Tech')
        if custom_url:
            try:
                parsed = feedparser.parse(custom_url)
                feed_name = parsed.feed.title if hasattr(parsed, 'feed') and hasattr(parsed.feed, 'title') else "Custom Feed"
                if not CustomFeed.query.filter_by(url=custom_url).first():
                    new_feed = CustomFeed(name=feed_name, url=custom_url, category=category)
                    db.session.add(new_feed)
                    db.session.commit()
            except Exception as e:
                print(f"Error adding custom feed: {e}")
        return redirect(url_for('index'))

    # Load custom feeds from database and append to categories
    active_categories = {cat: list(sources) for cat, sources in CATEGORY_SOURCES.items()}
    try:
        custom_feeds = CustomFeed.query.all()
        for cf in custom_feeds:
            cat = cf.category if cf.category in active_categories else "Tech"
            active_categories[cat].append({"name": cf.name, "url": cf.url})
    except Exception:
        pass

    # Fetch articles grouped by category concurrently
    news_by_category = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_cat = {}
        for cat, sources in active_categories.items():
            for src in sources:
                future = executor.submit(fetch_feed_entries, src['name'], src['url'])
                future_to_cat[future] = cat
        
        for future in as_completed(future_to_cat):
            cat = future_to_cat[future]
            name, entries = future.result()
            if entries:
                if cat not in news_by_category:
                    news_by_category[cat] = {}
                news_by_category[cat][name] = entries

    # Market ticker data fallback/mock for live display
    market_data = {
        "USD/JPY": "153.61",
        "Bitcoin": "$92,500",
        "GBP/USD": "1.3523"
    }

    try:
        saved_count = SavedArticle.query.count()
    except:
        saved_count = 0

    return render_template(
        'index.html',
        news_by_category=news_by_category,
        market_data=market_data,
        saved_count=saved_count
    )

@app.route('/save', methods=['POST'])
def save_article():
    title = request.form.get('title')
    link = request.form.get('link')
    source = request.form.get('source')
    if title and link:
        if not SavedArticle.query.filter_by(link=link).first():
            article = SavedArticle(title=title, link=link, source=source)
            db.session.add(article)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
