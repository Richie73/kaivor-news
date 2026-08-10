	mport os, requests, feedparser, logging, time
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

# --- SYSTEM LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_TITANIUM")

app = Flask(__name__)

# --- THE TITANIUM DATABASE HANDLER ---
def get_safe_uri():
    u = os.environ.get('DB_USER', 'postgres')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME', 'postgres')
    
    if all([u, p, h]):
        try:
            # Use quote_plus to stop special characters from crashing the app
            safe_p = quote_plus(p)
            # Port 6543 is the Supabase Transaction Pooler (Much more stable for Render)
            return f"postgresql+psycopg2://{u}:{safe_p}@{h}:6543/{n}?sslmode=require"
        except: pass
    
    logger.warning("CLOUD DB CONFIG INCOMPLETE: Switching to Local Storage.")
    return "sqlite:///survival_mode.db"

# Initialize App Config
app.config['SQLALCHEMY_DATABASE_URI'] = get_safe_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 280}

db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# Self-Healing Sync
with app.app_context():
    try:
        db.create_all()
        STATUS_MSG = "CONNECTED"
    except Exception as e:
        logger.error(f"DATABASE ERROR: {e}")
        # Final safety fallback
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///emergency_fallback.db"
        db.create_all()
        STATUS_MSG = "LOCAL_MODE"

# AI Intelligence Setup
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    ai_engine = genai.GenerativeModel('gemini-1.5-flash')
except:
    ai_engine = None

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except: feeds = []

    news_data, market = {}, []
    
    # 1. Market Ticker (High-Speed Binance Feed)
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
        m2 = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", timeout=1).json()
        market.append({"symbol": "ETH", "price": f"${float(m2['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. Weather
    weather = {"temp": "21", "desc": "ACTIVE"}
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=1).json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main'].upper()}
        except: pass

    # 3. News Processing (Spoofing Pro Desktop Headers)
    logo_token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for f in feeds:
        try:
            # We fetch raw then parse to bypass Anti-Bot systems
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            if p.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news_data[f.name] = {
                    "logo": f"https://img.logo.dev/{domain}?token={logo_token}",
                    "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:6]]
                }
        except: continue

    return render_template('index.html', news=news_data, weather=weather, market=market, status=STATUS_MSG)

@app.route('/add', methods=['POST'])
def add():
    name, url = request.form.get('name'), request.form.get('url')
    if name and url:
        try:
            if url.startswith("http://"): url = url.replace("http://", "https://")
            db.session.add(Feed(name=name, url=url))
            db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    try:
        if ai_engine:
            res = ai_engine.generate_content(f"In 15 words: {title}")
            return jsonify({"summary": res.text})
    except: pass
    return jsonify({"summary": "AI Intel Service Busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
