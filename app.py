import os, requests, feedparser, logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- DATABASE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h, n]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n}?sslmode=require"
    return "sqlite:///kaivor_permanent.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

with app.app_context():
    try: db.create_all()
    except: pass

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = []
    try: feeds = Feed.query.all()
    except: pass
    
    news_grouped = {}
    
    # 1. GUARDIAN API
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10"
            g_res = requests.get(g_url, timeout=5).json()
            news_grouped['World Trending'] = {
                "logo": "https://img.logo.dev/theguardian.com?token=" + os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': r['webTitle'], 'link': r['webUrl'], 'img': r.get('fields', {}).get('thumbnail')} for r in g_res['response']['results']]
            }
        except: pass

    # 2. RSS FEEDS
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                img = None
                if 'media_thumbnail' in e: img = e.media_thumbnail[0]['url']
                elif 'media_content' in e: img = e.media_content[0]['url']
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
            news_grouped[f.name] = {"logo": f"https://img.logo.dev/{domain}?token={token}", "articles": articles}
        except: continue

    # 3. EXPANDED FINANCIAL DATA (Coinbase + Yahoo Alternative)
    market = []
    try:
        # Crypto
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
        eth = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot").json()
        market.append({"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"})
        market.append({"s": "ETH", "p": f"${float(eth['data']['amount']):,.0f}"})
        # Global Indicators (Using a free public JSON summary)
        ext = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        market.append({"s": "GBP/USD", "p": round(1/ext['rates']['GBP'], 3)})
        market.append({"s": "EUR/USD", "p": round(1/ext['rates']['EUR'], 3)})
    except: market = [{"s": "MARKET", "p": "LIVE"}]

    return render_template('index.html', news=news_grouped, market=market)

@app.route('/add', methods=['POST'])
def add():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        try:
            db.session.add(Feed(name=n, url=u)); db.session.commit()
        except: db.session.rollback()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"Significance in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
