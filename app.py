import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- ZERO-FAILURE DATABASE LOGIC ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        # Use Port 6543 to bypass Render's IPv6 networking block
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    return "sqlite:///kaivor_vault.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500)); cat = db.Column(db.String(50))

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500)); link = db.Column(db.String(500)); img = db.Column(db.String(500)); source = db.Column(db.String(100))

with app.app_context():
    try: db.create_all()
    except: pass

# AI SETUP
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_rss(url, limit=5):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.0'}
        r = requests.get(url, headers=h, timeout=5)
        p = feedparser.parse(r.content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')} for e in p.entries[:limit]]
    except: return []

@app.route('/')
def index():
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    user_feeds = Feed.query.all()
    
    # A-F CATEGORY ARCHITECTURE
    intel = {
        "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml", 5),
        "World": [], # Filled by NYT below
        "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", 5),
        "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml", 5),
        "Tech": fetch_rss("https://www.theverge.com/rss/index.xml", 5),
        "Music": fetch_rss("https://www.nme.com/news/music/feed", 5)
    }
    
    # NYT API for World Prestige
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/world.json?api-key={nyt_key}").json()
            intel['World'] = [{'title': a['title'], 'link': a['url'], 'img': a['multimedia'][0]['url'] if a.get('multimedia') else None} for a in r['results'][:5]]
        except: pass
    
    # Fallback if NYT fails
    if not intel['World']: intel['World'] = fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml", 5)

    return render_template('index.html', intel=intel, bookmarks=bookmarks, user_feeds=user_feeds)

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Find the official RSS for {topic}. Return ONLY JSON: {{\"n\": \"Site\", \"u\": \"URL\", \"c\": \"Category\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Feed(name=d['n'], url=d['u'], cat=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'])); db.session.commit()
    return jsonify({"status": "success"})

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intelligence currently syncing..."})

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    f = Feed.query.get(id); db.session.delete(f); db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
