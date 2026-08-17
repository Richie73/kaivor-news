import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_FINAL")
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE ENGINE ---
def get_db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri: return uri.replace("postgres://", "postgresql://", 1)
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]): return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return 'sqlite:///kaivor_final_prod.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), unique=True)
    img = db.Column(db.String(500))
    source = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    try: db.create_all()
    except: pass

# --- ADVANCED IMAGE EXTRACTION ---
def fetch_hd_intel(url, name, limit=10):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/4.0'}
        r = requests.get(url, headers=h, timeout=10)
        p = feedparser.parse(r.content)
        for e in p.entries[:limit]:
            img = None
            # 1. Check for High-Res Enclosure (Standard for HQ News)
            if 'links' in e:
                for link in e.links:
                    if 'image' in link.get('type', ''): img = link.href
            # 2. Check for Media Content (Largest size usually last)
            if not img and 'media_content' in e:
                img = e.media_content[-1]['url']
            # 3. Check for NYT specific media
            if not img and 'media_thumbnail' in e:
                img = e.media_thumbnail[-1]['url']
            
            # 4. Upscale BBC Thumbnails (Hack to force HD)
            if img and "ichef.bbci.co.uk" in img:
                img = img.replace("/144/", "/800/").replace("/240/", "/800/")

            articles.append({'title': e.title, 'link': e.link, 'img': img, 'source': name})
    except: pass
    return articles

@app.route('/')
def index():
    matrix = {
        "UK": fetch_hd_intel("https://feeds.bbci.co.uk/news/uk/rss.xml", "BBC"),
        "World": fetch_hd_intel("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC"),
        "Markets": fetch_hd_intel("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "CNBC"),
        "Sport": fetch_hd_intel("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport"),
        "Tech": fetch_hd_intel("https://www.theverge.com/rss/index.xml", "Verge")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            if 'results' in r:
                matrix['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{"url":None}])[0]['url'], 'source': 'NYT'} for a in r['results'][:10]]
        except: pass

    saved = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', matrix=matrix, saved=saved)

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        if not Bookmark.query.filter_by(link=d['link']).first():
            db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source']))
            db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return jsonify({"summary": "AI Key Error."})
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        res = requests.post(url, json={"contents": [{"parts":[{"text": f"Explain in 1 sentence: {t}"}]}]}, timeout=8).json()
        return jsonify({"summary": res['candidates'][0]['content']['parts'][0]['text']})
    except: return jsonify({"summary": "Service busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
