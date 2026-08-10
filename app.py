import os, requests, feedparser, logging, time
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_TITANIUM")

app = Flask(__name__)

def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        try:
            return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
        except: pass
    return "sqlite:///fallback.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

with app.app_context():
    try:
        db.create_all()
        SYSTEM_STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DB Error: {e}")
        SYSTEM_STATUS = "LOCAL_STORAGE"

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    ai = genai.GenerativeModel('gemini-1.5-flash')
except: ai = None

@app.route('/')
def index():
    try: feeds = Feed.query.all()
    except: feeds = []
    news, market, weather = {}, [], {"temp": "--", "desc": "ACTIVATE"}
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric", timeout=1).json()
            weather = {"temp": int(w['main']['temp']), "desc": w['weather'][0]['main'].upper()}
        except: pass
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=4)
            p = feedparser.parse(r.content)
            if p.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news[f.name] = {"logo": f"https://img.logo.dev/{domain}?token={token}", "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:6]]}
        except: continue
    return render_template('index.html', news=news, weather=weather, market=market, status=SYSTEM_STATUS)

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
        res = ai.generate_content(f"Significance in 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
