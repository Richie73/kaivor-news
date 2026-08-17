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

# --- DATABASE LOGIC ---
def get_db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri: return uri.replace("postgres://", "postgresql://", 1)
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]): return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return 'sqlite:///kaivor_vault_v4.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Feed(db.Model):
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

# --- ADVANCED HD IMAGE EXTRACTION ---
def fetch_hd_intel(url, category, name, limit=12):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        r = requests.get(url, headers=h, timeout=10)
        p = feedparser.parse(r.content)
        for e in p.entries[:limit]:
            img = None
            # Scan for High-Res Enclosures first
            if 'links' in e:
                for link in e.links:
                    if 'image' in link.get('type', ''): img = link.href
            # Scan for Media Tags
            if not img and 'media_content' in e: img = e.media_content[0]['url']
            if not img and 'media_thumbnail' in e: img = e.media_thumbnail[-1]['url']
            # Clean tiny thumbnails (e.g. if image is less than 200px)
            if img and "144" in img: img = img.replace("144", "600") 
            
            articles.append({
                'title': e.title, 'article_url': e.link, 'image_url': img,
                'source_name': name, 'category': category
            })
    except: pass
    return articles

@app.route('/')
def index():
    matrix = {
        "UK": fetch_hd_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC"),
        "World": fetch_hd_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC World"),
        "Markets": fetch_hd_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC"),
        "Sport": fetch_hd_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport"),
        "Tech": fetch_hd_intel("https://www.theverge.com/rss/index.xml", "Tech", "The Verge"),
        "Culture": fetch_hd_intel("https://www.nme.com/news/music/feed", "Culture", "NME")
    }
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            if 'results' in r:
                matrix['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{"url":None}])[0]['url'], 'source': 'NYT', 'cat': 'World'} for a in r['results'][:10]]
        except: pass

    saved = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', matrix=matrix, saved=saved, status="SYSTEM_ONLINE")

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        if not Bookmark.query.filter_by(link=d['link']).first():
            db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'], cat=d['cat']))
            db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return jsonify({"summary": "AI Key Missing."})
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        payload = {"contents": [{"parts":[{"text": f"In 15 words, why does this matter: {t}"}]}]}
        res = requests.post(url, json=payload, timeout=8).json()
        return jsonify({"summary": res['candidates'][0]['content']['parts'][0]['text']})
    except: return jsonify({"summary": "AI Busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
