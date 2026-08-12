import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- STABLE CLOUD DATABASE LOGIC ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h, n]):
        # quote_plus handles your special characters (*, !, ) perfectly
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_emergency.db"

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
    db.create_all()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def get_news(url, count=5):
    try:
        p = feedparser.parse(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')} for e in p.entries[:count]]
    except: return []

@app.route('/')
def index():
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    # A-F CATEGORY MAPPING
    intel = {
        "UK": get_news("https://feeds.bbci.co.uk/news/uk/rss.xml", 3),
        "World": [],
        "Markets": get_news("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", 3),
        "Sport": get_news("https://feeds.bbci.co.uk/sport/football/rss.xml", 3),
        "Tech": [],
        "Music": get_news("https://www.nme.com/news/music/feed", 3)
    }
    
    # Fill World with NYT
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            intel['World'] = [{'title': a['title'], 'link': a['url'], 'img': a['multimedia'][0]['url'] if a.get('multimedia') else None} for a in r['results'][:3]]
        except: pass

    # Fill Tech with Hacker News
    try:
        r = requests.get("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=3").json()
        intel['Tech'] = [{'title': a['title'], 'link': a['url'] or f"https://news.ycombinator.com/item?id={a['objectID']}", 'img': None} for a in r['hits']]
    except: pass

    return render_template('index.html', intel=intel, bookmarks=bookmarks, feeds=Feed.query.all())

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source']))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Find official RSS for {topic}. Return JSON: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Feed(name=d['n'], url=d['u'], cat=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"Explain in 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intel Syncing..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
