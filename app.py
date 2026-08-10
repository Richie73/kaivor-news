import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__)

# --- SELF-HEALING DATABASE LOGIC ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h, n]):
        # Encode password just in case
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# Diagnostics Variable
SYSTEM_MSG = "INITIALIZING..."

with app.app_context():
    try:
        db.create_all()
        db.session.execute(db.text("SELECT 1"))
        SYSTEM_MSG = "CLOUD_CONNECTED"
    except Exception as e:
        logger.error(f"DB ERROR: {e}")
        # FAILSAFE: Switch to local database if cloud fails
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///kaivor_local.db"
        db.create_all()
        SYSTEM_MSG = f"LOCAL_MODE: {str(e)[:20]}"

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except: feeds = []
    
    news = {}
    market = []
    
    # 1. Market Ticker
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

    # 3. News (Spoofing Desktop Browser)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

    return render_template('index.html', news=news, weather=weather, market=market, status=SYSTEM_MSG)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            # Force HTTPS for stability
            if u.startswith("http://"): u = u.replace("http://", "https://")
            new_feed = Feed(name=n, url=u)
            db.session.add(new_feed)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Add failed: {e}")
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
