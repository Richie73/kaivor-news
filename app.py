import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__)

# --- THE TITANIUM ENGINE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h, n]):
        # Use Port 6543 (Pooler) and safe password encoding
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n}?sslmode=require"
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

# Boot protection
with app.app_context():
    try:
        db.create_all()
        STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DB Error: {e}")
        STATUS = "LOCAL_MODE"

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def fetch_rss(url, limit=5):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.0'}
        r = requests.get(url, headers=h, timeout=4)
        p = feedparser.parse(r.content)
        return [{'title': e.title, 'link': e.link, 'img': e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')} for e in p.entries[:limit]]
    except: return []

@app.route('/')
def index():
    # A-F CATEGORY LOGIC
    intel = {
        "UK": fetch_rss("https://feeds.bbci.co.uk/news/uk/rss.xml"),
        "World": fetch_rss("https://feeds.bbci.co.uk/news/world/rss.xml"),
        "Markets": fetch_rss("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance"),
        "Sport": fetch_rss("https://feeds.bbci.co.uk/sport/football/rss.xml"),
        "Tech": fetch_rss("https://www.theverge.com/rss/index.xml"),
        "Culture": fetch_rss("https://www.nme.com/news/music/feed")
    }
    
    # Financial Market Logic
    market = []
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market = [{"s": "BTC", "v": f"${float(btc['data']['amount']):,.0f}"}, {"s": "GOLD", "v": "$2,452"}, {"s": "S&P 500", "v": "5,510"}]
    except: market = [{"s": "TERMINAL", "v": "LIVE"}]

    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    return render_template('index.html', intel=intel, market=market, bookmarks=bookmarks, status=STATUS)

@app.route('/bookmark', methods=['POST'])
def bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'])); db.session.commit()
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
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Processing..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
