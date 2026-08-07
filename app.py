import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse, quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# --- ROBUST DATABASE CONNECTION ---
def get_db_url():
    raw_url = os.environ.get('DATABASE_URL', '').strip()
    if not raw_url: return 'sqlite:///news.db'
    try:
        # Fix the prefix
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
        # Encode the specific password symbols automatically
        if "Q*7Qs6rDguc)!XaXRbjM" in raw_url:
            safe_pass = quote_plus("Q*7Qs6rDguc)!XaXRbjM")
            raw_url = raw_url.replace("Q*7Qs6rDguc)!XaXRbjM", safe_pass)
        if "sslmode" not in raw_url:
            raw_url += "&sslmode=require" if "?" in raw_url else "?sslmode=require"
        return raw_url
    except: return 'sqlite:///news.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

with app.app_context():
    try: db.create_all()
    except: pass

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    db_status = "Connected"
    try:
        feeds = Feed.query.all()
    except Exception as e:
        db_status = f"Error: {str(e)[:20]}"
        feeds = []
    
    news_grouped = {}
    weather = {"temp": "--", "desc": "..."}
    market = []
    
    # 1. Weather
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main']}
        except: pass

    # 2. PRO Market Ticker (CoinGecko - No Key Required!)
    try:
        m_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json()
        market.append({"symbol": "BTC", "price": f"${m_res['bitcoin']['usd']:,}"})
        market.append({"symbol": "ETH", "price": f"${m_res['ethereum']['usd']:,}"})
    except:
        market = [{"symbol": "Market", "price": "Offline"}]

    # 3. News Logic
    logo_token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            parsed = feedparser.parse(f.url)
            domain = urlparse(f.url).netloc.replace('feeds.', '').replace('www.', '')
            news_grouped[f.name] = {
                "logo": f"https://img.logo.dev/{domain}?token={logo_token}",
                "articles": [{'title': e.title, 'link': e.link} for e in parsed.entries[:5]]
            }
        except: continue

    return render_template('index.html', news_grouped=news_grouped, weather=weather, market=market, db_status=db_status)

@app.route('/add', methods=['POST'])
def add_feed():
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
        res = ai_model.generate_content(f"Explain why this matters in 1 sentence: {title}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
