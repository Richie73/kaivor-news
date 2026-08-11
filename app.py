import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor_vault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100)); url = db.Column(db.String(500))

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500)); link = db.Column(db.String(500)); img = db.Column(db.String(500)); source = db.Column(db.String(100))

with app.app_context():
    db.create_all()

# AI Setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    feeds = Feed.query.all()
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    news = {}

    # 1. NYT TOP STORIES
    nyt_key = os.environ.get('NYT_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}", timeout=5).json()
            news['NYT: Top Stories'] = {"logo": "https://img.logo.dev/nytimes.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['title'], 'link': a['url'], 'img': a['multimedia'][0]['url'] if a.get('multimedia') else None} for a in r['results'][:6]]}
        except: pass

    # 2. GUARDIAN WORLD
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            r = requests.get(f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=8", timeout=5).json()
            news['Guardian: World'] = {"logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results']]}
        except: pass

    # 3. RSS SIGNALS
    token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            r = requests.get(f.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                img = e.media_thumbnail[0]['url'] if 'media_thumbnail' in e else None
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            news[f.name] = {"logo": f"https://img.logo.dev/{f.url.split('//')[-1].split('/')[0]}?token={token}", "articles": articles}
        except: continue

    # 4. MARKET WATCH (Expanded)
    market = []
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market = [{"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"}, {"s": "GOLD", "p": "$2,458"}, {"s": "S&P 500", "p": "5,522"}, {"s": "NASDAQ", "p": "18,010"}]
    except: market = [{"s": "MARKETS", "p": "LIVE"}]

    return render_template('index.html', news=news, market=market, bookmarks=bookmarks, feeds=feeds)

# --- NEW GLOBAL SEARCH ROUTE ---
@app.route('/search', methods=['POST'])
def search_news():
    query = request.json.get('query')
    key = os.environ.get('GNEWS_API_KEY')
    if not key: return jsonify([])
    try:
        url = f"https://gnews.io/api/v4/search?q={query}&lang=en&max=6&apikey={key}"
        r = requests.get(url).json()
        results = [{'title': a['title'], 'link': a['url'], 'img': a['image'], 'source': a['source']['name']} for a in r['articles']]
        return jsonify(results)
    except: return jsonify([])

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source']))
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
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI Offline."})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic')
    key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Find a valid RSS feed URL for {topic}. Return JSON ONLY: {{\"n\": \"Name\", \"u\": \"URL\"}}"
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, 
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        data = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
        db.session.add(Feed(name=data['n'], url=data['u'])); db.session.commit()
        return jsonify({"status": "success", "name": data['n']})
    except: return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
