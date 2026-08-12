import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus, urlparse, urljoin
from datetime import datetime
import google.generativeai as genai

# --- SYSTEM ARCHITECTURE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_OS")
app = Flask(__name__, template_folder='app/templates')

# --- RESILIENT DATABASE LOGIC ---
# Default to local storage to guarantee 100% Uptime on Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor_vault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), unique=True)
    cat = db.Column(db.String(50))

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), unique=True)
    img = db.Column(db.String(500))
    source = db.Column(db.String(100))
    cat = db.Column(db.String(50))
    is_saved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- INTELLIGENCE SERVICES ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def ingest(url, category="General", source_name="Signal", limit=5):
    articles = []
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/2.0'}
        r = requests.get(url, headers=h, timeout=5)
        feed = feedparser.parse(r.content)
        for e in feed.entries[:limit]:
            img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
            articles.append({'title': e.title, 'link': e.link, 'img': img, 'source': source_name, 'cat': category})
    except: pass
    return articles

@app.route('/')
def dashboard():
    # A-F CATEGORY MAPPING
    matrix = {
        "UK": ingest("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC"),
        "World": [],
        "Markets": ingest("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC"),
        "Sport": ingest("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport"),
        "Tech": ingest("https://www.theverge.com/rss/index.xml", "Tech", "The Verge"),
        "Culture": ingest("https://www.nme.com/news/music/feed", "Culture", "NME")
    }
    
    # World News API (NYT)
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/world.json?api-key={nyt_key}").json()
            matrix["World"] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url'), 'source': 'NYT', 'cat': 'World'} for a in r['results'][:5]]
        except: pass
    if not matrix["World"]: matrix["World"] = ingest("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC World")

    saved = Article.query.filter_by(is_saved=True).all()
    return render_template('index.html', matrix=matrix, saved=saved)

@app.route('/intel/save', methods=['POST'])
def save():
    d = request.json
    if not Article.query.filter_by(link=d['link']).first():
        db.session.add(Article(title=d['title'], link=d['link'], img=d['img'], source=d['source'], cat=d['cat'], is_saved=True))
        db.session.commit()
    return jsonify({"status": "success"})

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic')
    key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Identify the primary RSS feed for {topic}. Return ONLY JSON: {{'n': 'Source Name', 'u': 'RSS URL'}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.io"},
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        data = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        # Automatic Ingestion
        db.session.add(Source(name=data['n'], url=data['u'], cat="Discovery"))
        db.session.commit()
        return jsonify({"status": "success", "name": data['n']})
    except: return jsonify({"status": "failed"})

@app.route('/intel/brief', methods=['POST'])
def brief():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
