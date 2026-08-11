import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_IRONCLAD")

app = Flask(__name__)

# --- THE TITANIUM ENGINE (V2) ---
def get_db_uri():
    u = os.environ.get('DB_USER', '').strip()
    p = os.environ.get('DB_PASSWORD', '').strip()
    h = os.environ.get('DB_HOST', '').strip()
    n = os.environ.get('DB_NAME', 'postgres').strip()
    
    if all([u, p, h]):
        # Removed complex engine options to prevent TypeErrors
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# INITIALIZATION: This creates the "Lifeboat" automatically
with app.app_context():
    try:
        db.create_all()
        # Ensure at least one source exists (BBC)
        if not Feed.query.filter_by(name='BBC World').first():
            db.session.add(Feed(name='BBC World', url='https://feeds.bbci.co.uk/news/rss.xml'))
            db.session.commit()
        STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DATABASE FAILSAFE: {e}")
        STATUS = "LOCAL_STORAGE_ACTIVE"

# AI SETUP
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    ai = genai.GenerativeModel('gemini-1.5-flash')
except: ai = None

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except: feeds = []
    
    news, market = {}, []
    
    # 1. Market (Binance)
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=2).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. Weather
    w_key = os.environ.get('WEATHER_KEY')
    weather = {"temp": "23", "desc": "ACTIVE"}
    if w_key:
        try:
            w = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=2).json()
            weather = {"temp": int(w['main']['temp']), "desc": w['weather'][0]['main'].upper()}
        except: pass

    # 3. News Signals (BBC hardcoded failsafe)
    if not feeds:
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

    return render_template('index.html', news=news, market=market, weather=weather, status=STATUS)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            if u.startswith("http://"): u = u.replace("http://", "https://")
            db.session.add(Feed(name=n, url=u))
            db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intelligence Syncing..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
