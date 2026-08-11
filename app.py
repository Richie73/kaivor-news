import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__)

# --- CLEAN DATABASE LOGIC ---
def get_db_uri():
    u = os.environ.get('DB_USER')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME', 'postgres')
    
    if all([u, p, h]):
        # The industrial standard connection string
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_permanent.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# Auto-Sync
with app.app_context():
    try:
        db.create_all()
        # Ensure BBC is ALWAYS there as a baseline
        if not Feed.query.filter_by(name='BBC World').first():
            db.session.add(Feed(name='BBC World', url='https://feeds.bbci.co.uk/news/rss.xml'))
            db.session.commit()
        STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DB Error: {e}")
        STATUS = "LOCAL_ACTIVE"

# AI Configuration
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    ai = genai.GenerativeModel('gemini-1.5-flash')
except: ai = None

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except: feeds = []
    
    news, market = {}, []
    
    # 1. Market (Cloud-safe Coinbase API)
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
        eth = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot").json()
        market = [
            {"symbol": "BTC", "price": f"${float(btc['data']['amount']):,.0f}"},
            {"symbol": "ETH", "price": f"${float(eth['data']['amount']):,.0f}"}
        ]
    except: market = [{"symbol": "MARKET", "price": "LIVE"}]

    # 2. News (Spoofing desktop headers to prevent blocks)
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    token = os.environ.get('LOGODEV_TOKEN')
    
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                # Find images in different RSS formats
                img = None
                if 'media_thumbnail' in e: img = e.media_thumbnail[0]['url']
                elif 'media_content' in e: img = e.media_content[0]['url']
                
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
            news[f.name] = {
                "logo": f"https://img.logo.dev/{domain}?token={token}",
                "articles": articles
            }
        except: continue

    return render_template('index.html', news=news, market=market, status=STATUS)

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
        res = ai.generate_content(f"In 1 short sentence, why is this important: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing service busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
