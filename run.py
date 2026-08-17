import os, requests, feedparser, logging, json, re, hashlib, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus, urlparse
from datetime import datetime

# --- SYSTEM CORE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_PRO")
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE ARCHITECTURE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return os.environ.get('DATABASE_URL', 'sqlite:///kaivor_vault.db').replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), unique=True)
    cat = db.Column(db.String(50))

class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), unique=True)
    img = db.Column(db.String(500))
    source = db.Column(db.String(100))
    cat = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    try: db.create_all()
    except: pass

# --- INTELLIGENCE SERVICES ---
def fetch_intel(url, name="Source", limit=10):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Kaivor/5.0'}
        r = requests.get(url, headers=h, timeout=6)
        p = feedparser.parse(r.content)
        articles = []
        for e in p.entries[:limit]:
            # HIGH-RES IMAGE LOGIC
            img = None
            if 'media_content' in e: img = e.media_content[-1]['url']
            elif 'enclosure' in e: img = e.enclosure['url']
            elif 'media_thumbnail' in e: img = e.media_thumbnail[-1]['url']
            
            # Clean title
            title = e.title.split(' - ')[0] if ' - ' in e.title else e.title
            articles.append({'title': title, 'link': e.link, 'img': img, 'source': name})
        return articles
    except: return []

@app.route('/')
def index():
    # A-F CURATED INTELLIGENCE MATRIX
    matrix = {
        "UK": fetch_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "BBC"),
        "World": fetch_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "World Intel"),
        "Markets": fetch_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "CNBC"),
        "Sport": fetch_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC Sport"),
        "Tech": fetch_intel("https://www.theverge.com/rss/index.xml", "The Verge"),
        "Music": fetch_intel("https://www.nme.com/news/music/feed", "NME")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            if 'results' in r:
                matrix['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url'), 'source': 'NYT'} for a in r['results'][:10]]
        except: pass

    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', matrix=matrix, saved=bookmarks, status="TERMINAL_ACTIVE")

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    if not Bookmark.query.filter_by(link=d['link']).first():
        db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'], cat=d['cat']))
        db.session.commit()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
