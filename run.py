import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_OS")
app = Flask(__name__, template_folder='app/templates')

# --- PRODUCTION DATABASE LOGIC ---
DATABASE_URL = os.environ.get('DATABASE_URL')
def get_db_uri():
    if DATABASE_URL:
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
    category = db.Column(db.String(50), default='General')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    content_hash = db.Column(db.String(64), unique=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- HIGH-DEFINITION INGESTION ---
def fetch_hd_intel(url, category, name, limit=10):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        r = requests.get(url, headers=h, timeout=8)
        p = feedparser.parse(r.content)
        for e in p.entries[:limit]:
            # Digging for the high-res image
            img = None
            if 'links' in e:
                for link in e.links:
                    if 'image' in link.get('type', ''): img = link.href
            if not img and 'media_content' in e: img = e.media_content[0]['url']
            if not img and 'media_thumbnail' in e: img = e.media_thumbnail[-1]['url']
            
            articles.append({
                'title': e.title, 'article_url': e.link, 'image_url': img,
                'source_name': name, 'category': category
            })
    except: pass
    return articles

@app.route('/')
def index():
    # A-F CATEGORY MATRIX (POPULATED AUTOMATICALLY)
    matrix = {
        "UK": fetch_hd_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC"),
        "World": fetch_hd_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC World"),
        "Markets": fetch_hd_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC"),
        "Sport": fetch_hd_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport"),
        "Tech": fetch_hd_intel("https://www.theverge.com/rss/index.xml", "Tech", "The Verge"),
        "Culture": fetch_hd_intel("https://www.nme.com/news/music/feed", "Culture", "NME")
    }
    
    saved = db.session.query(Article).join(Library).all()
    return render_template('index.html', matrix=matrix, saved=saved, status="TERMINAL_ACTIVE")

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        if not Article.query.filter_by(article_url=d['link']).first():
            new_a = Article(title=d['title'], article_url=d['link'], image_url=d['img'], source_name=d['source'], category=d['cat'], content_hash=hashlib.sha256(d['link'].encode()).hexdigest())
            db.session.add(new_a); db.session.flush()
            db.session.add(Library(article_id=new_a.id)); db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. Return ONLY JSON: {{'n': 'Name', 'u': 'URL', 'c': 'Category'}}"
        headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.io"}
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        raw = res['choices'][0]['message']['content']
        d = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group(0))
        db.session.add(Source(name=d['n'], feed_url=d['u'], category=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
