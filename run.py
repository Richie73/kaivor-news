import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime
import google.generativeai as genai

# --- SYSTEM ARCHITECTURE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_OS")
app = Flask(__name__, template_folder='app/templates')

# --- RESILIENT DATABASE LOGIC ---
def get_db_uri():
    # 1. Try direct DATABASE_URL (Neon/Postgres)
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri.replace("postgres://", "postgresql://", 1)
    
    # 2. Try split variables (Supabase)
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    
    # 3. Fallback to local
    return 'sqlite:///kaivor_vault_v2.db'

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
    db.create_all()

# --- INTELLIGENCE SERVICES ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_rss(url, limit=4):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/3.0'}
        r = requests.get(url, headers=h, timeout=5)
        p = feedparser.parse(r.content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')} for e in p.entries[:limit]]
    except: return []

@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def index():
    # A-F CATEGORY MATRIX
    intel = {
        "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml"),
        "World": fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml"),
        "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance"),
        "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml"),
        "Tech": fetch_rss("https://www.theverge.com/rss/index.xml"),
        "Music": fetch_rss("https://www.nme.com/news/music/feed")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            if 'results' in r:
                intel['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url')} for a in r['results'][:4]]
        except: pass

    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', intel=intel, bookmarks=bookmarks, status="CONNECTED")

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
    try:
        res = ai.generate_content(f"Explain in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intel Offline."})

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. Return JSON: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Source(name=d['n'], url=d['u'], cat=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
