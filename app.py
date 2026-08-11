import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor_core.db'
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

    # 1. PROFESSIONAL MARKET DATA (yfinance)
    market = []
    try:
        # Tickers: ^GSPC (S&P500), ^IXIC (NASDAQ), GC=F (Gold), CL=F (Crude Oil)
        tickers = {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "GC=F": "GOLD", "CL=F": "CRUDE OIL"}
        data = yf.download(list(tickers.keys()), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        for sym, name in tickers.items():
            price = data[sym]
            market.append({"s": name, "p": f"${price:,.2f}" if price < 100 else f"${price:,.0f}"})
        
        # Crypto (Coinbase)
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot").json()
        market.insert(0, {"s": "BITCOIN", "p": f"${float(btc['data']['amount']):,.0f}"})
    except Exception as e:
        print(f"Market Error: {e}")
        market = [{"s": "MARKETS", "p": "LIVE"}]

    # 2. NEWS APIS (NYT & GUARDIAN)
    nyt_key, g_key = os.environ.get('NYT_API_KEY'), os.environ.get('GUARDIAN_API_KEY')
    if nyt_key:
        try:
            r = requests.get(f"https://api.nytimes.com/svc/topstories/v2/home.json?api-key={nyt_key}").json()
            news['World Report'] = {"cat": "World", "logo": "https://img.logo.dev/nytimes.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['title'], 'link': a['url'], 'img': a['multimedia'][0]['url'] if a.get('multimedia') else None} for a in r['results'][:6]]}
        except: pass
    if g_key:
        try:
            r = requests.get(f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=8").json()
            news['Global Briefing'] = {"cat": "World", "logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results']]}
        except: pass

    # 3. RSS SIGNALS
    token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            p = feedparser.parse(requests.get(f.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).content)
            articles = []
            for e in p.entries[:5]:
                img = e.media_thumbnail[0]['url'] if 'media_thumbnail' in e else (e.media_content[0]['url'] if 'media_content' in e else None)
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            news[f.name] = {"cat": f.category, "logo": f"https://img.logo.dev/{f.url.split('//')[-1].split('/')[0]}?token={token}", "articles": articles}
        except: continue

    return render_template('index.html', news=news, market=market, bookmarks=bookmarks, feeds=feeds)

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"Explain in 1 sentence: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing service busy."})

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'])); db.session.commit()
    return jsonify({"status": "success"})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Find the official RSS for {topic}. Return JSON ONLY: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
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
