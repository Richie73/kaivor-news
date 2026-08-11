import os, requests, feedparser, logging, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_RESCUE")

app = Flask(__name__)

# --- THE LIFEBOAT ENGINE ---
def get_db_uri():
    u = os.environ.get('DB_USER', '').strip()
    p = os.environ.get('DB_PASSWORD', '').strip()
    h = os.environ.get('DB_HOST', '').strip()
    n = os.environ.get('DB_NAME', 'postgres').strip()
    if all([u, p, h]):
        # We try the standard port; if networking fails, we catch it later
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///local_safe.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_timeout": 5}
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# This ensures the app starts even if the DB is unreachable
with app.app_context():
    try:
        db.create_all()
    except:
        logger.error("Initial DB sync failed, will retry on page load.")

@app.route('/')
def index():
    status = "CLOUD_ACTIVE"
    try:
        # Try fetching from Cloud
        feeds = Feed.query.all()
    except Exception:
        # IF CLOUD FAILS (Network unreachable): Switch to local instantly
        logger.warning("Network Unreachable. Deploying Lifeboat (Local Storage).")
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///local_safe.db"
        with app.app_context():
            db.create_all()
            feeds = Feed.query.all()
        status = "LOCAL_SAFE_MODE"

    news, market = {}, []
    
    # 1. Market Ticker
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=2).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. News Logic (BBC hardcoded if empty)
    if not feeds:
        # If no feeds yet, show BBC by default so user sees something
        feeds = [type('obj', (object,), {'name': 'BBC World', 'url': 'https://feeds.bbci.co.uk/news/rss.xml'})]

    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.0'}
    
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            if p.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news[f.name] = {
                    "logo": f"https://img.logo.dev/{domain}?token={token}",
                    "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:5]]
                }
        except: continue

    return render_template('index.html', news=news, market=market, status=status)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            db.session.add(Feed(name=n, url=u))
            db.session.commit()
        except:
            db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        ai = genai.GenerativeModel('gemini-1.5-flash')
        res = ai.generate_content(f"Significance in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intelligence currently syncing..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
