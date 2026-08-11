import os, requests, feedparser, logging, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

app = Flask(__name__)

# --- THE "STAY ALIVE" DATABASE LOGIC ---
def get_db_uri():
    u = os.environ.get('DB_USER', '').strip()
    p = os.environ.get('DB_PASSWORD', '').strip()
    h = os.environ.get('DB_HOST', '').strip()
    n = os.environ.get('DB_NAME', 'postgres').strip()
    
    if all([u, p, h]):
        # Port 6543 is the Supabase Pooler (Highest stability)
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n}?sslmode=require"
    return "sqlite:///emergency.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# INITIALIZATION
SYSTEM_INFO = "INIT"
try:
    with app.app_context():
        db.create_all()
        # Auto-add BBC if missing
        if not Feed.query.filter_by(name='BBC').first():
            db.session.add(Feed(name='BBC', url='https://feeds.bbci.co.uk/news/rss.xml'))
            db.session.commit()
    SYSTEM_INFO = "DATABASE_READY"
except Exception as e:
    SYSTEM_INFO = f"DB_ERROR: {str(e)[:30]}"

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
        news, market = {}, []
        
        # 1. Market Ticker
        try:
            m = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=2).json()
            market.append({"symbol": "BTC", "price": f"${float(m['price']):,.0f}"})
        except: market = [{"symbol": "MKT", "price": "LIVE"}]

        # 2. News Logic (Professional Desktop Spoofing)
        token = os.environ.get('LOGODEV_TOKEN')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kaivor/1.0'}
        
        for f in feeds:
            try:
                r = requests.get(f.url, headers=headers, timeout=5)
                p = feedparser.parse(r.content)
                if p.entries:
                    domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
                    news[f.name] = {
                        "logo": f"https://img.logo.dev/{domain}?token={token}",
                        "articles": [{'title': e.title, 'link': e.link} for e in p.entries[:5]]
                    }
            except: continue

        return render_template('index.html', news=news, market=market, status=SYSTEM_INFO)

    except Exception as e:
        # If the app crashes, show the error on the screen
        return f"<h1>Kaivor Core Crash</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>", 500

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
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        ai = genai.GenerativeModel('gemini-1.5-flash')
        res = ai.generate_content(f"Significance in 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intelligence Offline."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
