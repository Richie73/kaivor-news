import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- CLEAN DATABASE CONNECTION ---
def get_db_uri():
    u, pw, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, pw, h, n]):
        return f"postgresql://{u}:{pw}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///fallback.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

with app.app_context():
    db.create_all()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
        status = "CONNECTED"
    except:
        feeds, status = [], "OFFLINE"

    news = {}
    market = []
    # Fast Ticker
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()
        market = [{"symbol": "BTC", "price": f"${float(m['price']):,.0f}"}]
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # Weather
    w_key = os.environ.get('WEATHER_KEY')
    weather = {"temp": "23", "desc": "CLEAR"}
    if w_key:
        try:
            w = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w['main']['temp']), "desc": w['weather'][0]['main'].upper()}
        except: pass

    # News (Spoofing Desktop Browser)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','')
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
        db.session.add(Feed(name=n, url=u)); db.session.commit()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    return jsonify({"summary": ai.generate_content(f"Explain in 15 words: {t}").text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
