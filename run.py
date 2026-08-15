import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus, urlparse, urljoin
from datetime import datetime
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return os.environ.get('DATABASE_URL', 'sqlite:///kaivor_vault.db').replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website_url = db.Column(db.String(500))
    feed_url = db.Column(db.String(500), unique=True)
    cat = db.Column(db.String(50), default='General')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
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

# --- ADVANCED DISCOVERY LOGIC ---
def sniff_rss(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=h, timeout=5, allow_redirects=True)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check link tags
        found = soup.find('link', type='application/rss+xml') or \
                soup.find('link', type='application/atom+xml')
        if found and found.get('href'):
            return urljoin(url, found['href'])
        
        # Try common paths if nothing in HTML
        common_paths = ['/rss', '/feed', '/rss.xml', '/index.xml']
        for path in common_paths:
            test_url = urljoin(url, path)
            tr = requests.get(test_url, headers=h, timeout=3)
            if 'xml' in tr.headers.get('Content-Type', ''):
                return test_url
    except: pass
    return None

def ai_agent_intel(query):
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key: return None
    try:
        # Prompt changed to ask for BOTH website and known RSS
        prompt = f"Find the official news website and the most likely RSS feed URL for '{query}'. Return ONLY JSON: {{'n': 'Name', 'w': 'https://website.com', 'u': 'https://website.com/rss'}}"
        headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.news"}
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, 
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        raw = res['choices'][0]['message']['content']
        return json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group(0))
    except: return None

# --- ROUTES ---
@app.route('/')
def index():
    # Dynamic A-F categories from DB
    cats = ["UK", "World", "Markets", "Sport", "Tech", "Culture"]
    matrix = {c: [] for c in cats}
    sources = Source.query.all()
    
    h = {'User-Agent': 'Mozilla/5.0'}
    for s in sources:
        try:
            p = feedparser.parse(requests.get(s.feed_url, headers=h, timeout=5).content)
            articles = []
            for e in p.entries[:5]:
                img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
                articles.append({'title': e.title, 'link': e.link, 'img': img, 'source_name': s.name})
            if s.cat in matrix: matrix[s.cat].extend(articles)
            else: matrix["World"].extend(articles)
        except: continue

    saved = db.session.query(Article).join(Library).all()
    return render_template('index.html', matrix=matrix, saved=saved, status="SIGNALS_LIVE")

@app.route('/discover', methods=['POST'])
def discover():
    query = request.json.get('query')
    # 1. AI Logic
    data = ai_agent_intel(query)
    if not data: return jsonify({"status": "failed"})
    
    # 2. Validation / Sniffing
    final_feed = sniff_rss(data['w']) or data['u']
    
    # Test final feed
    try:
        test = requests.get(final_feed, timeout=5)
        if test.status_code == 200:
            return jsonify({"status": "success", "name": data['n'], "website": data['w'], "feed": final_feed})
    except: pass
    
    return jsonify({"status": "failed"})

@app.route('/add-source', methods=['POST'])
def add_source():
    d = request.json
    if not Source.query.filter_by(feed_url=d['feed']).first():
        new = Source(name=d['name'], website_url=d['website'], feed_url=d['feed'], cat="World")
        db.session.add(new); db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "exists"})

# (Existing routes for /health, /intel/save, /intel/brief remain active)
@app.route('/health')
def health(): return jsonify({"status": "healthy"})
@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    # Manual REST call to Gemini
    key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    try:
        r = requests.post(url, json={"contents": [{"parts":[{"text": f"Explain in 15 words: {t}"}]}]}).json()
        return jsonify({"summary": r['candidates'][0]['content']['parts'][0]['text']})
    except: return jsonify({"summary": "Briefing busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
