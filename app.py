import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__)

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

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai = genai.GenerativeModel('gemini-1.5-flash')

def get_rss_from_html(url):
    """Scans a website for hidden RSS links."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        rss = soup.find('link', type='application/rss+xml') or soup.find('link', type='application/atom+xml')
        if rss: return urljoin(url, rss['href'])
    except: pass
    return None

@app.route('/')
def index():
    feeds = Feed.query.all()
    bookmarks = Bookmark.query.order_by(Bookmark.id.desc()).all()
    news = {}
    
    # 1. GUARDIAN API
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            r = requests.get(f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10", timeout=5).json()
            news['Global Briefing'] = {"logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results']]}
        except: pass

    # 2. RSS SIGNALS
    token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            r = requests.get(f.url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            p = feedparser.parse(r.content)
            articles = []
            for e in p.entries[:5]:
                img = e.media_thumbnail[0]['url'] if 'media_thumbnail' in e else (e.media_content[0]['url'] if 'media_content' in e else None)
                articles.append({'title': e.title, 'link': e.link, 'img': img})
            news[f.name] = {"logo": f"https://img.logo.dev/{f.url.split('//')[-1].split('/')[0]}?token={token}", "articles": articles}
        except: continue

    # 3. MARKET DATA
    market = []
    try:
        btc = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=2).json()
        market = [{"s": "BTC", "p": f"${float(btc['data']['amount']):,.0f}"}, {"s": "GOLD", "p": "$2,458"}, {"s": "S&P 500", "p": "5,522"}, {"s": "NASDAQ", "p": "18,010"}]
    except: market = [{"s": "MARKET", "p": "LIVE"}]

    return render_template('index.html', news=news, market=market, bookmarks=bookmarks, feeds=feeds)

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic')
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key: return jsonify({"status": "failed", "msg": "API Key Missing"})

    try:
        # 1. Ask DeepSeek for the official website or RSS
        prompt = f"Provide ONLY the official URL of a news website or RSS feed for '{topic}'. Return JSON: {{\"n\": \"Name\", \"u\": \"URL\"}}"
        headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": "https://kaivor.news", "X-Title": "Kaivor"}
        
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, 
            json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
        
        ai_raw = res['choices'][0]['message']['content']
        data = json.loads(re.search(r'\{.*\}', ai_raw, re.DOTALL).group(0))
        
        target_url = data['u']
        
        # 2. Sniff the URL to find the ACTUAL RSS link if the AI gave a homepage
        actual_rss = target_url if 'rss' in target_url or 'xml' in target_url or 'feed' in target_url else get_rss_from_html(target_url)
        
        if not actual_rss:
            # Final attempt: common patterns
            actual_rss = urljoin(target_url, "/rss") if target_url.endswith('/') else target_url + "/rss"

        if not Feed.query.filter_by(url=actual_rss).first():
            db.session.add(Feed(name=data['n'], url=actual_rss))
            db.session.commit()
            return jsonify({"status": "success", "name": data['n']})
        return jsonify({"status": "exists"})
    except Exception as e:
        logger.error(f"Agent Logic Error: {e}")
        return jsonify({"status": "failed", "msg": str(e)})

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
    except: return jsonify({"summary": "Briefing service busy."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
