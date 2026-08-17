import os, requests, feedparser, logging, json, re, hashlib, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime
from bs4 import BeautifulSoup

# --- SYSTEM ARCHITECTURE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_PROD")
app = Flask(__name__, template_folder='app/templates')

# --- RESILIENT DATABASE CONFIGURATION ---
def get_db_uri():
    # Priority 1: DATABASE_URL (Standard Render/Neon)
    uri = os.environ.get('DATABASE_URL')
    if uri:
        uri = uri.replace("postgres://", "postgresql://", 1)
    else:
        # Priority 2: Split Variables (Supabase Pooler)
        u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
        if all([u, p, h]):
            uri = f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}"
    
    # Final Fallback (Development Only)
    return uri or "sqlite:///kaivor_dev.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CRITICAL: Fix for "SSL connection closed unexpectedly"
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,   # Detects dead connections before using them
    "pool_recycle": 280,     # Refreshes connections before Render/Neon timeouts
    "pool_size": 10,
    "max_overflow": 5
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- PRODUCTION DATA MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website_url = db.Column(db.String(500))
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General')
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'))
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    content_hash = db.Column(db.String(64), unique=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# Database Initialization
with app.app_context():
    try:
        db.create_all()
        logger.info("Database Synchronized.")
    except Exception as e:
        logger.error(f"Startup DB Error: {e}")

# --- GEMINI SDK MIGRATION (google.genai compatible) ---
def ai_briefing(title):
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return "Intelligence key missing."
    try:
        # Using REST fallback for maximum compatibility with Python 3.14/Mobile
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {"contents": [{"parts":[{"text": f"Explain in 15 words why this matters: {title}"}]}]}
        res = requests.post(url, json=payload, timeout=8).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"AI Briefing failed: {e}")
        return "Intelligence service busy."

# --- NEWS INGESTION SERVICE ---
def fetch_intel(url, category, name, limit=8):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Kaivor/5.0'}
        r = requests.get(url, headers=h, timeout=6)
        p = feedparser.parse(r.content)
        for e in p.entries[:limit]:
            # Deduplication
            uid = hashlib.sha256(e.link.encode()).hexdigest()
            img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
            articles.append({'title': e.title, 'link': e.link, 'img': img, 'source': name, 'cat': category, 'hash': uid})
    except: pass
    return articles

# --- ROUTES ---
@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "reason": str(e)}), 500

@app.route('/')
def index():
    try:
        # A-F CURATED INTELLIGENCE
        matrix = {
            "UK": fetch_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC"),
            "World": fetch_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC"),
            "Markets": fetch_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC"),
            "Sport": fetch_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport"),
            "Tech": fetch_intel("https://www.theverge.com/rss/index.xml", "Tech", "The Verge"),
            "Culture": fetch_intel("https://www.nme.com/news/music/feed", "Culture", "NME")
        }
        
        # Pull Bookmarks through Library Join
        saved = db.session.query(Article).join(Library).order_by(Library.saved_at.desc()).all()
        return render_template('index.html', matrix=matrix, saved=saved, status="CONNECTED")
    except Exception as e:
        logger.error(f"Dashboard Error: {e}")
        return f"<h1>KAIVOR ERROR</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    return jsonify({"summary": ai_briefing(t)})

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

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. Return ONLY JSON: {{'n': 'Name', 'u': 'URL', 'c': 'Category'}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        if not Source.query.filter_by(feed_url=d['u']).first():
            db.session.add(Source(name=d['n'], feed_url=d['u'], category=d['c']))
            db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
