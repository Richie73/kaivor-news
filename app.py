import os, requests, feedparser, logging, json
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
    db.create_all()

# --- AI AGENTS SETUP ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini = genai.GenerativeModel('gemini-1.5-flash')

def deepseek_agent(prompt):
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key: return None
    try:
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "system", "content": "You are a news signal agent. Return ONLY valid JSON."},
                             {"role": "user", "content": prompt}]
            })
        ).json()
        return res['choices'][0]['message']['content']
    except: return None

@app.route('/')
def index():
    feeds = []
    try: feeds = Feed.query.all()
    except: pass
    
    news_grouped = {}
    
    # 1. GUARDIAN API (Trending)
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=8"
            g_res = requests.get(g_url, timeout=5).json()
            news_grouped['World Trending'] = {
                "logo": "https://img.logo.dev/theguardian.com?token=" + os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': r['webTitle'], 'link': r['webUrl'], 'img': r.get('fields', {}).get('thumbnail')} for r in g_res['response']['results']]
            }
        except: pass

    # 2. RSS FEED SIGNALS
    token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            r = requests.get(f.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                img = e.media_thumbnail[0]['url'] if 'media_thumbnail' in e else (e.media_content[0]['url'] if 'media_content' in e else None)
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','').replace('feeds.','')
            news_grouped[f.name] = {"logo": f"https://img.logo.dev/{domain}?token={token}", "articles": articles}
        except: continue

    # 3. EXPANDED FINANCIAL DATA (Indestructible Multi-Source)
    market = []
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
        market.append({"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"})
        # Global Markets (Simulated for speed, can use Alpha Vantage for precision)
        market.append({"s": "S&P 500", "p": "5,495"})
        market.append({"s": "GOLD", "p": "$2,410"})
        market.append({"s": "NASDAQ", "p": "17,120"})
    except: market = [{"s": "MARKET", "p": "LIVE"}]

    return render_template('index.html', news=news_grouped, market=market)

@app.route('/auto-discover', methods=['POST'])
def auto_discover():
    topic = request.json.get('topic')
    # Use DeepSeek to find a reliable RSS feed URL for the topic
    prompt = f"Find the official RSS feed URL for {topic}. Return a JSON object with 'name' and 'url'. Example: {{'name': 'The Verge', 'url': 'https://www.theverge.com/rss/index.xml'}}"
    ai_response = deepseek_agent(prompt)
    if ai_response:
        try:
            data = json.loads(ai_response.strip())
            new_feed = Feed(name=data['name'], url=data['url'])
            db.session.add(new_feed)
            db.session.commit()
            return jsonify({"status": "success", "source": data['name']})
        except: pass
    return jsonify({"status": "failed"})

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = gemini.generate_content(f"In 15 words, why is this important: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing service busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
