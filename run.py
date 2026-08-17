import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, template_folder='app/templates')

# --- THE STABLE DATABASE ENGINE ---
def get_db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri.replace("postgres://", "postgresql://", 1)
    return 'sqlite:///kaivor_permanent.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- THE GOOGLE NEWS STYLE MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    # This was the crashing column - we've made it safe here
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'), nullable=True)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# Ensure tables exist
with app.app_context():
    try: db.create_all()
    except: pass

# --- THE GOOGLE NEWS INGESTION ENGINE ---
def fetch_news(url, name="Global", limit=10):
    try:
        h = {'User-Agent': 'Mozilla/5.0 Kaivor/5.0'}
        r = requests.get(url, headers=h, timeout=5)
        p = feedparser.parse(r.content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url'), 'source': name} for e in p.entries[:limit]]
    except: return []

@app.route('/')
def index():
    # A-F CATEGORY MAPPING (Like Google News Sections)
    matrix = {
        "UK": fetch_news("https://feeds.bbci.co.uk/news/uk/rss.xml", "BBC"),
        "Markets": fetch_news("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "CNBC"),
        "Sport": fetch_news("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC Sport"),
        "Tech": fetch_news("https://www.theverge.com/rss/index.xml", "The Verge"),
        "Culture": fetch_news("https://www.nme.com/news/music/feed", "NME")
    }
    
    # Check Library
    try:
        saved = db.session.query(Article).join(Library).all()
    except: saved = []
    
    return render_template('index.html', matrix=matrix, saved=saved, status="SYSTEM_ONLINE")

# ... (AI Briefing and Save Logic from before)
@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    key = os.environ.get("GEMINI_API_KEY")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        res = requests.post(url, json={"contents": [{"parts":[{"text": f"In 15 words: {t}"}]}]}, timeout=8).json()
        return jsonify({"summary": res['candidates'][0]['content']['parts'][0]['text']})
    except: return jsonify({"summary": "AI Busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
