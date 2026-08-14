import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_ST1_FINAL")
app = Flask(__name__, template_folder='app/templates')

# --- PRODUCTION DATABASE LOGIC (NEON ONLY) ---
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_uri():
    if DATABASE_URL:
        # Standardize for SQLAlchemy
        return DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return 'sqlite:///kaivor_permanent.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50))

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- INTELLIGENCE SERVICES ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_rss(url, limit=5):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.5'}
        r = requests.get(url, headers=h, timeout=5)
        p = feedparser.parse(r.content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')} for e in p.entries[:limit]]
    except: return []

@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def index():
    # A-F CATEGORY LOGIC
    matrix = {
        "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml"),
        "World": [],
        "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance"),
        "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml"),
        "Tech": fetch_rss("https://www.theverge.com/rss/index.xml"),
        "Culture": fetch_rss("https://www.nme.com/news/music/feed")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/world.json?api-key={nyt_key}").json()
            matrix["World"] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url')} for a in r['results'][:5]]
        except: pass
    if not matrix["World"]: matrix["World"] = fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml")

    # Fetch bookmarks from persistent Library table
    try:
        saved = db.session.query(Article).join(Library).all()
    except: saved = []
    
    return render_template('index.html', matrix=matrix, saved=saved, status="NEON_PERSISTENCE")

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        article = Article.query.filter_by(article_url=d['link']).first()
        if not article:
            article = Article(title=d['title'], article_url=d['link'], image_url=d['img'], source_name=d['source'], category=d['cat'])
            db.session.add(article)
            db.session.flush()
        if not Library.query.filter_by(article_id=article.id).first():
            db.session.add(Library(article_id=article.id))
            db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"Significance in 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI briefing failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
