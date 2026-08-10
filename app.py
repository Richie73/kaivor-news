import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- THE SUPABASE CONNECTION (HEAVILY PROTECTED) ---
def get_db_uri():
    u = os.environ.get('DB_USER', 'postgres')
    p = os.environ.get('DB_PASSWORD', 'KaivorNews2026') # Change if you reset it
    h = os.environ.get('DB_HOST', 'db.dvzofvhpczawhvnbncfi.supabase.co')
    n = os.environ.get('DB_NAME', 'postgres')
    
    if p and h:
        # Use quote_plus for the password and force the IPv4 pooler port 5432
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# INITIALIZATION: Add BBC by default so it's NEVER empty
with app.app_context():
    try:
        db.create_all()
        if not Feed.query.filter_by(name='BBC World').first():
            db.session.add(Feed(name='BBC World', url='https://feeds.bbci.co.uk/news/rss.xml'))
            db.session.commit()
        STATUS = "CONNECTED"
    except Exception as e:
        STATUS = "LOCAL_MODE"

# AI SETUP
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = []
    try: feeds = Feed.query.all()
    except: pass
    
    news, market = {}, []
    # Binance Ticker
    try:
        m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=1).json()
        market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # News Fetching (Improved Headers)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KaivorNews/1.0'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            if p.entries:
                domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                news[f.name] = {
                    "logo": f"https://img.logo.dev/{domain}?token={token}",
                    "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:6]]
                }
        except: continue

    return render_template('index.html', news=news, market=market, status=STATUS)

@app.route('/add', methods=['POST'])
def add():
    name = request.form.get('name')
    url = request.form.get('url')
    if name and url:
        try:
            if url.startswith("http://"): url = url.replace("http://", "https://")
            db.session.add(Feed(name=name, url=url))
            db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Brief unavailable."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
