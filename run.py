import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus, urlparse, urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai

# --- PRODUCTION CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__, template_folder='app/templates')

def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        # Use Port 6543 (Supabase Pooler) for high-stability cloud networking
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return "sqlite:///kaivor_vault.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATA MODELS ---
class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General')

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), unique=True)
    img = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    hash = db.Column(db.String(64), unique=True)
    is_saved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- INTELLIGENCE SERVICES ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_and_normalize(url, name="Global", limit=5):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KaivorEngine/1.1'}
        r = requests.get(url, headers=h, timeout=6)
        feed = feedparser.parse(r.content)
        for e in feed.entries[:limit]:
            # Deduplication logic
            uid = hashlib.sha256(e.link.encode()).hexdigest()
            img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
            articles.append({
                'id': uid, 'title': e.title, 'link': e.link, 'img': img, 'source': name
            })
    except Exception as e:
        logger.error(f"Ingestion failed for {name}: {e}")
    return articles

# --- CORE ROUTES ---
@app.route('/')
def dashboard():
    # A-F STRUCTURED INTELLIGENCE MATRIX
    matrix = {
        "UK": fetch_and_normalize("https://feeds.bbci.co.uk/news/uk/rss.xml", "BBC UK"),
        "World": fetch_and_normalize("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
        "Markets": fetch_and_normalize("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "CNBC"),
        "Sport": fetch_and_normalize("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC Sport"),
        "Tech": fetch_and_normalize("https://www.theverge.com/rss/index.xml", "The Verge"),
        "Culture": fetch_and_normalize("https://www.nme.com/news/music/feed", "NME")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}", timeout=5).json()
            matrix['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url'), 'source': 'NYT'} for a in r['results'][:5]]
        except: pass

    saved = Article.query.filter_by(is_saved=True).order_by(Article.created_at.desc()).all()
    return render_template('index.html', matrix=matrix, saved=saved)

@app.route('/agent/discover', methods=['POST'])
def discover():
    topic = request.json.get('topic')
    key = os.environ.get('OPENROUTER_API_KEY')
    prompt = f"Find the official RSS feed for {topic}. Return ONLY valid JSON: {{'n': 'Name', 'u': 'URL', 'c': 'Category'}}"
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.io"},
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        data = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        # Validate before adding
        test = requests.get(data['u'], timeout=5)
        if test.status_code == 200:
            new_source = Source(name=data['n'], url=data['u'], category=data['c'])
            db.session.add(new_source); db.session.commit()
            return jsonify({"status": "success", "data": data})
    except: pass
    return jsonify({"status": "failed"})

@app.route('/intel/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words, why is this headline critical: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Intelligence offline."})

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    if not Article.query.filter_by(link=d['link']).first():
        db.session.add(Article(title=d['title'], link=d['link'], img=d['img'], source_name=d['source'], is_saved=True))
        db.session.commit()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
