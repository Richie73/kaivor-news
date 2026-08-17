import os, requests, feedparser, logging, json, re, hashlib, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime

# --- SYSTEM ARCHITECTURE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_PROD")
app = Flask(__name__, template_folder='app/templates')

# --- RESILIENT DATABASE CONFIGURATION ---
def get_db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        uri = uri.replace("postgres://", "postgresql://", 1)
    else:
        u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
        if all([u, p, h]):
            uri = f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}"
    return uri or "sqlite:///kaivor_permanent.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 280}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- PRODUCTION MODELS (SCHEMA TRUTH) ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    publisher_name = db.Column(db.String(100))
    website_url = db.Column(db.String(500))
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General')
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'), nullable=True) # Nullable for migration safety
    source_name = db.Column(db.String(100)) # Preserves legacy source strings
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50))
    content_hash = db.Column(db.String(64), unique=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- GEMINI REST INTEGRATION ---
def ai_briefing(title):
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return "Key missing."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        res = requests.post(url, json={"contents": [{"parts":[{"text": f"In 15 words: {title}"}]}]}, timeout=8).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except: return "AI Intel offline."

# --- NEWS INGESTION ---
def fetch_intel(url, category, name, limit=8):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 Kaivor/5.0'}
        p = feedparser.parse(requests.get(url, headers=h, timeout=6).content)
        for e in p.entries[:limit]:
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
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def index():
    try:
        matrix = {
            "UK": fetch_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC"),
            "World": fetch_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC"),
            "Markets": fetch_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC"),
            "Sport": fetch_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport"),
            "Tech": fetch_intel("https://www.theverge.com/rss/index.xml", "Tech", "The Verge"),
            "Culture": fetch_intel("https://www.nme.com/news/music/feed", "Culture", "NME")
        }
        # Join Article and Library for persistent bookmarks
        saved = db.session.query(Article).join(Library).order_by(Library.saved_at.desc()).all()
        return render_template('index.html', matrix=matrix, saved=saved, status="CONNECTED")
    except Exception as e:
        logger.error(f"UI Error: {e}")
        return f"<h1>KAIVOR SCHEMA ERROR</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/intel/brief', methods=['POST'])
def brief():
    return jsonify({"summary": ai_briefing(request.json.get('title'))})

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        art = Article.query.filter_by(article_url=d['link']).first()
        if not art:
            art = Article(title=d['title'], article_url=d['link'], image_url=d['img'], source_name=d['source'], category=d['cat'])
            db.session.add(art); db.session.flush()
        if not Library.query.filter_by(article_id=art.id).first():
            db.session.add(Library(article_id=art.id))
        db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.io"}
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": f"RSS for {topic}. Return JSON: {{'n': 'Name', 'u': 'URL', 'c': 'Category'}}"}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        if not Source.query.filter_by(feed_url=d['u']).first():
            db.session.add(Source(name=d['n'], feed_url=d['u'], category=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
