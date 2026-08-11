import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_PRO")

app = Flask(__name__)

def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

with app.app_context():
    try:
        db.create_all()
        if not Feed.query.filter_by(name='BBC World').first():
            db.session.add(Feed(name='BBC World', url='https://feeds.bbci.co.uk/news/rss.xml'))
            db.session.commit()
        STATUS = "CLOUD_SYNCED"
    except:
        STATUS = "LOCAL_ACTIVE"

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    ai = genai.GenerativeModel('gemini-1.5-flash')
except: ai = None

@app.route('/')
def index():
    try: feeds = Feed.query.all()
    except: feeds = []
    
    news, market = {}, []
    
    # 1. Market (Using Coinbase API - more reliable for cloud servers)
    try:
        m_btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market.append({"symbol": "BTC", "price": f"${float(m_btc['data']['amount']):,.0f}"})
        m_eth = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=2).json()
        market.append({"symbol": "ETH", "price": f"${float(m_eth['data']['amount']):,.0f}"})
    except: market = [{"symbol": "MKT", "price": "LIVE"}]

    # 2. News (Deep Image Extraction)
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.0'}
    
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:6]:
                # Deep Image Search (checks enclosure, media:thumbnail, and content)
                img = None
                if 'media_thumbnail' in e and e.media_thumbnail:
                    img = e.media_thumbnail[0]['url']
                elif 'media_content' in e and e.media_content:
                    img = e.media_content[0]['url']
                elif 'links' in e:
                    for link in e.links:
                        if 'image' in link.get('type', ''):
                            img = link.href
                
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
            news[f.name] = {
                "logo": f"https://img.logo.dev/{domain}?token={token}",
                "articles": articles
            }
        except: continue

    return render_template('index.html', news=news, market=market, weather={"temp":"23","desc":"ACTIVE"}, status=STATUS)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            if u.startswith("http://"): u = u.replace("http://", "https://")
            db.session.add(Feed(name=n, url=u)); db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Thinking..."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
