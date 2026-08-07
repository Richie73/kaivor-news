import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# Database
def get_db_url():
    raw_url = os.environ.get('DATABASE_URL', '').strip()
    if not raw_url: return 'sqlite:///news.db'
    if raw_url.startswith("postgres://"): raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    if "postgresql" in raw_url and "sslmode" not in raw_url:
        raw_url += "&sslmode=require" if "?" in raw_url else "?sslmode=require"
    return raw_url

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

with app.app_context():
    db.create_all()

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = Feed.query.all()
    news_grouped = {}
    
    # 1. Weather & Stocks
    weather = {"temp": "--", "desc": "..."}
    market = []
    
    w_key = os.environ.get('WEATHER_KEY')
    s_key = os.environ.get('STOCK_KEY')

    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main']}
        except: pass

    if s_key:
        try:
            # Fetching Bitcoin price as an example
            s_res = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=BTCUSD&apikey={s_key}").json()
            price = float(s_res['Global Quote']['05. price'])
            market.append({"symbol": "BTC", "price": f"${price:,.0f}"})
        except: pass

    # 2. News Logic
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

    return render_template('index.html', news_grouped=news_grouped, weather=weather, market=market)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    try:
        response = ai_model.generate_content(f"Why this matters in 1 short sentence: {title}")
        return jsonify({"summary": response.text})
    except: return jsonify({"summary": "Brief unavailable."})

@app.route('/add', methods=['POST'])
def add_feed():
    db.session.add(Feed(name=request.form.get('name'), url=request.form.get('url')))
    db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
