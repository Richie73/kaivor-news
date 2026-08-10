import os, requests, feedparser, logging, time
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_IRONCLAD")

app = Flask(__name__)

# --- DATABASE SURVIVAL LOGIC ---
def get_db_uri():
    u = os.environ.get('DB_USER')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME', 'postgres')
    
    # Use port 6543 (Supabase Pooler) instead of 5432 for better cloud compatibility
    if all([u, p, h]):
        try:
            safe_pw = quote_plus(p)
            # We use the Transaction Pooler port (6543) which is more reliable on Render
            return f"postgresql+psycopg2://{u}:{safe_pw}@{h}:6543/{n}?sslmode=require"
        except: pass
    
    return "sqlite:///survival_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# SAFETY BOX: This prevents "Exited with Status 1"
SYSTEM_MSG = "WAKING_UP"
with app.app_context():
    try:
        db.create_all()
        SYSTEM_MSG = "CLOUD_ACTIVE"
    except Exception as e:
        logger.error(f"CLOUD_DB_FAILED: {e}")
        # If Cloud fails, force local storage so the app STARTS
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///survival_local.db"
        db.create_all()
        SYSTEM_MSG = "LOCAL_STORAGE_MODE"

# AI SETUP
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except: feeds = []
    
    news = {}
    market = []
    
    # 1. Market (Binance)
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. Weather
    weather = {"temp": "23", "desc": "ACTIVE"}
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=1).json()
            weather = {"temp": int(w['main']['temp']), "desc": w['weather'][0]['main'].upper()}
        except: pass

    # 3. News (Spoofing Desktop)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=4)
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
            db.session.add(Feed(name=n, url=u))
            db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"Summarize in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Processing..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
