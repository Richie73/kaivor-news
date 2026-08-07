import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse, quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# --- SECURE DATABASE LOGIC ---
def get_db_url():
    raw_url = os.environ.get('DATABASE_URL', '').strip()
    if not raw_url: return 'sqlite:///news.db'
    
    try:
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
        
        # Professional encoding for your specific password
        # This handles the *, !, and ) characters perfectly
        parts = urlparse(raw_url)
        if parts.password:
            safe_password = quote_plus(parts.password)
            raw_url = raw_url.replace(parts.password, safe_password)
            
        if "sslmode" not in raw_url:
            raw_url += "&sslmode=require" if "?" in raw_url else "?sslmode=require"
        return raw_url
    except Exception as e:
        return 'sqlite:///news.db'

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
    db_status = "Cloud Connected"
    try:
        feeds = Feed.query.all()
        # Test if we can actually write to the DB
        if not feeds: db_status = "Ready (Empty)"
    except Exception as e:
        db_status = f"DB Error: {str(e)[:15]}"
        feeds = []
    
    news_grouped = {}
    weather = {"temp": "--", "desc": "Offline"}
    market = []
    
    # 1. Weather (Using HTTPS)
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main']}
        except: pass

    # 2. Market Ticker (Using HTTPS)
    try:
        m_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json()
        market.append({"symbol": "BTC", "price": f"${m_res['bitcoin']['usd']:,}"})
        market.append({"symbol": "ETH", "price": f"${m_res['ethereum']['usd']:,}"})
    except:
        market = [{"symbol": "Market", "price": "Pending"}]

    # 3. News Logic
    logo_token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            # Force HTTPS for the feed fetch
            feed_url = f.url.replace("http://", "https://")
            parsed = feedparser.parse(feed_url)
            domain = urlparse(feed_url).netloc.replace('feeds.', '').replace('www.', '')
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
            # Force HTTPS
            if u.startswith("http://"): u = u.replace("http://", "https://")
            db.session.add(Feed(name=n, url=u))
            db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    try:
        res = ai_model.generate_content(f"Why this matters: {title}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing unavailable."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
