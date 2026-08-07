import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__)

# --- INDUSTRIAL STRENGTH DATABASE LOGIC ---
def get_db_uri():
    u = os.environ.get('DB_USER')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME')
    
    if all([u, p, h, n]):
        # The 'psycopg2' driver is the most stable for Render to Supabase
        return f"postgresql+psycopg2://{u}:{p}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///emergency_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Auto-recovery for stale connections
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# Force-Sync Database
with app.app_context():
    try:
        db.create_all()
        db.session.execute(db.text("SELECT 1"))
        SYSTEM_STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DB FAILURE: {e}")
        SYSTEM_STATUS = "DB_AUTH_ERROR"

# AI Configuration
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
        status = SYSTEM_STATUS
    except:
        feeds, status = [], "DATABASE_OFFLINE"

    news = {}
    market = []
    
    # 1. Market Ticker (Binance API)
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=2).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except:
        market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. Weather
    w_key = os.environ.get('WEATHER_KEY')
    weather = {"temp": "23", "desc": "ACTIVE"}
    if w_key:
        try:
            w = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=2).json()
            weather = {"temp": int(w['main']['temp']), "desc": w['weather'][0]['main'].upper()}
        except: pass

    # 3. News Processing (Spoofing Desktop Headers)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    for f in feeds:
        try:
            # Crucial: Fetch raw data then parse (bypasses most blocks)
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            if p.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news[f.name] = {
                    "logo": f"https://img.logo.dev/{domain}?token={token}",
                    "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:5]]
                }
        except: continue

    return render_template('index.html', news=news, weather=weather, market=market, status=status)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            # Force HTTPS
            if u.startswith("http://"): u = u.replace("http://", "https://")
            db.session.add(Feed(name=n, url=u))
            db.session.commit()
            logger.info(f"ADDED: {n}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"ADD_FAILED: {e}")
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 1 short sentence, why is this important: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing service unavailable."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
