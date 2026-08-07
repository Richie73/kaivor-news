import os, requests, feedparser, logging, time
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import google.generativeai as genai

# Extreme Logging for troubleshooting
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_CORE")

app = Flask(__name__)

# --- IRONCLAD DATABASE ENGINE ---
def get_engine_url():
    user = os.environ.get('DB_USER', 'postgres')
    pw = os.environ.get('DB_PASSWORD', '')
    host = os.environ.get('DB_HOST', '')
    db_name = os.environ.get('DB_NAME', 'postgres')
    
    if not pw or not host:
        logger.warning("Cloud DB vars missing. Using local fallback.")
        return "sqlite:///news.db"
    
    # Critical: Encode special characters in password (*, !, )
    safe_pw = quote_plus(pw)
    return f"postgresql+psycopg2://{user}:{safe_pw}@{host}:5432/{db_name}?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = get_engine_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Engine optimization: detect stale connections automatically
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

with app.app_context():
    try:
        db.create_all()
        logger.info("SYSTEM: Database Synchronized.")
    except Exception as e:
        logger.error(f"SYSTEM: DB Sync Failed: {e}")

# AI Intelligence Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    start_time = time.time()
    try:
        feeds = Feed.query.all()
        db_status = "STABLE"
    except:
        feeds, db_status = [], "DATABASE_OFFLINE"

    news_grouped = {}
    weather = {"temp": "--", "desc": "WAKING..."}
    market = []

    # 1. Faster Weather Fetch
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_data = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=3).json()
            weather = {"temp": int(w_data['main']['temp']), "desc": w_data['weather'][0]['main'].upper()}
        except: pass

    # 2. Resilient Market Ticker
    try:
        m_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=3).json()
        market = [{"symbol": "BTC", "price": f"${m_data['bitcoin']['usd']:,}"}, {"symbol": "ETH", "price": f"${m_data['ethereum']['usd']:,}"}]
    except:
        market = [{"symbol": "MARKET", "price": "LIVE"}]

    # 3. Robust RSS Processor (Blocks bots/Mixed Content issues)
    logo_token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KaivorNews/1.0'}
    
    for f in feeds:
        try:
            # We use requests first to bypass "Bot Blockers" that feedparser hits
            resp = requests.get(f.url, headers=headers, timeout=5)
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news_grouped[f.name] = {
                    "logo": f"https://img.logo.dev/{domain}?token={logo_token}",
                    "articles": [{'title': e.title, 'link': e.link} for e in parsed.entries[:6]]
                }
        except Exception as e:
            logger.error(f"FEED_ERROR [{f.name}]: {e}")
            continue

    return render_template('index.html', news=news_grouped, weather=weather, market=market, status=db_status, load=round(time.time()-start_time, 2))

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
    title = request.json.get('title')
    try:
        response = ai.generate_content(f"In 15 words or less, explain the importance of: {title}")
        return jsonify({"summary": response.text})
    except: return jsonify({"summary": "Briefing unavailable at this time."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
