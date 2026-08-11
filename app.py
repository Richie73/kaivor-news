import os, requests, feedparser, logging, json
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- STABLE DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor_core.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    url = db.Column(db.String(500))
    category = db.Column(db.String(50), default='General')

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500))
    link = db.Column(db.String(500))
    img = db.Column(db.String(500))
    source = db.Column(db.String(100))

with app.app_context():
    db.create_all()

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = Feed.query.all()
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    news_grouped = {}
    
    # 1. PRIMARY SOURCE: THE GUARDIAN
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10"
            r = requests.get(g_url, timeout=5).json()
            news_grouped['Top Stories'] = {
                "logo": "https://img.logo.dev/theguardian.com?token=" + os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results']]
            }
        except: pass

    # 2. FOLLOWED SOURCES
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

    # 3. MARKET WATCH
    market = []
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market = [
            {"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"},
            {"s": "GOLD", "p": "$2,458"},
            {"s": "S&P 500", "p": "5,522"},
            {"s": "FTSE 100", "p": "8,210"}
        ]
    except: market = [{"s": "MARKETS", "p": "LIVE"}]

    return render_template('index.html', news=news_grouped, market=market, bookmarks=bookmarks, feeds=feeds)

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    data = request.json
    db.session.add(Bookmark(title=data['title'], link=data['link'], img=data['img'], source=data['source']))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    f = Feed.query.get(id); db.session.delete(f); db.session.commit()
    return redirect('/')

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words, why is this headline important: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Summarization unavailable."})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic')
    key = os.environ.get('OPENROUTER_API_KEY')
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "system", "content": "Return ONLY JSON: {'n': 'Name', 'u': 'RSS_URL'}"}, {"role": "user", "content": f"Find official RSS for {topic}"}]}).json()
        d = json.loads(res['choices'][0]['message']['content'].strip())
        db.session.add(Feed(name=d['n'], url=d['u'])); db.session.commit()
        return jsonify({"status": "success", "name": d['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
