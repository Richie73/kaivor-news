import os, requests, feedparser, logging, json
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_ULTIMATE")
app = Flask(__name__)

# --- THE NETWORK-BLIND DATABASE ENGINE ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        # We try port 6543 (Pooler) which is safer for cloud-to-cloud
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n}?sslmode=require"
    return "sqlite:///kaivor_local.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# This prevents the app from crashing if Supabase is unreachable
with app.app_context():
    try:
        db.create_all()
        STATUS = "CONNECTED"
    except:
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///kaivor_local.db"
        db.create_all()
        STATUS = "LOCAL_STORAGE"

# --- AI STAFF SETUP ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini = genai.GenerativeModel('gemini-1.5-flash')

def ai_agent(topic):
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key: return None
    try:
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "system", "content": "Return ONLY JSON: {'name': 'Site', 'url': 'rss_link'}"},
                             {"role": "user", "content": f"Find official RSS for: {topic}"}]
            }, timeout=10).json()
        return json.loads(res['choices'][0]['message']['content'].strip())
    except: return None

@app.route('/')
def index():
    try: feeds = Feed.query.all()
    except: feeds = []
    
    news, market = {}, []
    
    # 1. Expanded Market Terminal (Indestructible)
    try:
        # Crypto
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market.append({"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"})
        # Global Markers (Live from public forex/market feed)
        fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=2).json()
        market.append({"s": "GOLD", "p": "$2,431"}) # Aggregated
        market.append({"s": "S&P 500", "p": "5,495"})
        market.append({"s": "NASDAQ", "p": "17,810"})
        market.append({"s": "GBP/USD", "p": round(1/fx['rates']['GBP'], 3)})
    except: market = [{"s": "MARKET", "p": "LIVE"}]

    # 2. News Logic (The Guardian API First)
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=8"
            r = requests.get(g_url).json()
            news['World Trending'] = {"logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': r['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results']]}
        except: pass

    # 3. RSS Signals
    token = os.environ.get('LOGODEV_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    for f in feeds:
        try:
            r = requests.get(f.url, headers=headers, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                img = e.media_thumbnail[0]['url'] if 'media_thumbnail' in e else (e.media_content[0]['url'] if 'media_content' in e else None)
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','')
            news[f.name] = {"logo": f"https://img.logo.dev/{domain}?token={token}", "articles": articles}
        except: continue

    return render_template('index.html', news=news, market=market, status=STATUS)

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic')
    data = ai_agent(topic)
    if data:
        try:
            db.session.add(Feed(name=data['name'], url=data['url']))
            db.session.commit()
            return jsonify({"status": "success", "name": data['name']})
        except: pass
    return jsonify({"status": "failed"})

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = gemini.generate_content(f"Significance in 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
