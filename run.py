import os, requests, feedparser, logging, json, re, hashlib, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime

# --- SYSTEM ARCHITECTURE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_OS")
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE LOGIC ---
def get_db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri.replace("postgres://", "postgresql://", 1)
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return 'sqlite:///kaivor_vault_final.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELS ---
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
def fetch_rss(url, limit=8):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/5.0'}
        r = requests.get(url, headers=h, timeout=5)
        p = feedparser.parse(r.content)
        articles = []
        for e in p.entries[:limit]:
            img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
            articles.append({'title': e.title, 'link': e.link, 'img': img})
        return articles
    except: return []

# --- ROUTES ---
@app.route('/')
def index():
    try:
        # A-F CATEGORY MATRIX (PRO DATA)
        matrix = {
            "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml"),
            "World": fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml"),
            "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance"),
            "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml"),
            "Tech": fetch_rss("https://www.theverge.com/rss/index.xml"),
            "Culture": fetch_rss("https://www.nme.com/news/music/feed")
        }
        
        nyt_key = os.environ.get('NYT_API_KEY')
        if nyt_key:
            try:
                r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
                if 'results' in r:
                    matrix['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia', [{}])[0].get('url')} for a in r['results'][:8]]
            except: pass

        bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
        return render_template('index.html', matrix=matrix, saved=bookmarks, status="TERMINAL_ACTIVE")
    except Exception as e:
        return f"<body style='background:#000;color:red;padding:20px;'><h1>KAIVOR ERROR</h1><pre>{traceback.format_exc()}</pre></body>", 500

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    try:
        if not Bookmark.query.filter_by(link=d['link']).first():
            db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'], cat=d['cat']))
            db.session.commit()
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error"}), 500

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. Return ONLY JSON: {{'n': 'Name', 'u': 'URL', 'c': 'Category'}}"
        headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.io"}
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Source(name=d['n'], url=d['u'], cat=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
