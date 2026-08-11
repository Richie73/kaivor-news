import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor_vault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500)); category = db.Column(db.String(50), default='General')

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500)); link = db.Column(db.String(500)); img = db.Column(db.String(500)); source = db.Column(db.String(100))

with app.app_context():
    db.create_all()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = Feed.query.all()
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    news = {}
    categories = set(['Intelligence', 'Technology', 'Markets'])
    
    # 1. NEWSDATA.IO (BREAKING)
    nd_key = os.environ.get('NEWSDATA_KEY')
    if nd_key:
        try:
            url = f"https://newsdata.io/api/1/latest?apikey={nd_key}&country=gb,us&language=en&category=top&image=1"
            r = requests.get(url, timeout=5).json()
            news['Breaking Intel'] = {"cat": "Intelligence", "logo": "https://cdn-icons-png.flaticon.com/512/21/21601.png",
                "articles": [{'title': a['title'], 'link': a['link'], 'img': a.get('image_url')} for a in r['results'][:5]]}
        except: pass

    # 2. NYT & GUARDIAN
    nyt_key, g_key = os.environ.get('NYT_API_KEY'), os.environ.get('GUARDIAN_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            news['NYT'] = {"cat": "World", "logo": "https://img.logo.dev/nytimes.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['title'], 'link': a['url'], 'img': a['multimedia'][0]['url'] if a.get('multimedia') else None} for a in r['results'][:5]]}
        except: pass
    if g_key:
        try:
            r = requests.get(f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail").json()
            news['The Guardian'] = {"cat": "World", "logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results'][:5]]}
        except: pass

    # 3. MARKET DATA (Custom Ticker Data)
    market_str = "LOADING MARKET DATA..."
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
        eth = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot").json()
        market_str = f"BTC: ${float(btc['data']['amount']):,.0f}  •  ETH: ${float(eth['data']['amount']):,.0f}  •  S&P 500: 5,522.30  •  GOLD: $2,458.20  •  NASDAQ: 18,010.50  •  GBP/USD: 1.274"
    except: pass

    return render_template('index.html', news=news, market_str=market_str, bookmarks=bookmarks, categories=sorted(list(categories)))

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Intel Syncing..."})

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'])); db.session.commit()
    return jsonify({"status": "success"})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Find official RSS for {topic}. Return JSON: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        d = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Feed(name=d['n'], url=d['u'], category=d['c'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    f = Feed.query.get(id); db.session.delete(f); db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
