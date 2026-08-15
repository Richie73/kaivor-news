import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE ENGINE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h, n]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return "sqlite:///kaivor_vault.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500)); cat = db.Column(db.String(50))

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500)); link = db.Column(db.String(500)); img = db.Column(db.String(500)); source = db.Column(db.String(100))

with app.app_context():
    try: db.create_all()
    except: pass

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_rss(url, limit=10): # Increased limit
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        r = requests.get(url, headers=h, timeout=6)
        p = feedparser.parse(r.content)
        articles = []
        for e in p.entries[:limit]:
            img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
            articles.append({'title': e.title, 'link': e.link, 'img': img})
        return articles
    except: return []

@app.route('/')
def index():
    # A-F CATEGORY MAPPING (10 stories each)
    intel = {
        "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml"),
        "World": fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml"),
        "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance"),
        "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml"),
        "Tech": fetch_rss("https://www.theverge.com/rss/index.xml"),
        "Culture": fetch_rss("https://www.nme.com/news/music/feed")
    }
    
    # Premium NYT Layer
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            if 'results' in r:
                intel['World'] = [{'title': a['title'], 'link': a['url'], 'img': a.get('multimedia',[{}])[0].get('url')} for a in r['results'][:10]]
        except: pass

    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', intel=intel, bookmarks=bookmarks, status="CONNECTED")

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
    try:
        res = ai.generate_content(f"Significance in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intel Offline."})

@app.route('/agent/search', methods=['POST'])
def agent_search():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. Return JSON: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Feed(name=d['n'], url=d['u'], cat=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
