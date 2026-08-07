import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse, quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

def get_db_url():
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    host = os.environ.get('DB_HOST')
    port = os.environ.get('DB_PORT', '5432')
    name = os.environ.get('DB_NAME')
    if all([user, password, host, name]):
        safe_password = quote_plus(password)
        return f"postgresql://{user}:{safe_password}@{host}:{port}/{name}?sslmode=require"
    return 'sqlite:///news.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

with app.app_context():
    try: db.create_all()
    except Exception as e: logger.error(f"DB Error: {e}")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    db_status = "Connected"
    try:
        feeds = Feed.query.all()
    except:
        db_status = "Link Error"
        feeds = []
    
    news_grouped = {}
    weather = {"temp": "--", "desc": "Clear"}
    market = []
    
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main']}
        except: pass

    try:
        m_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=5).json()
        market.append({"symbol": "BTC", "price": f"${m_res['bitcoin']['usd']:,}"})
        market.append({"symbol": "ETH", "price": f"${m_res['ethereum']['usd']:,}"})
    except:
        market = [{"symbol": "Market", "price": "Live"}]

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
        res = ai_model.generate_content(f"Why this matters: {title}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
