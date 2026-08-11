import os, requests, feedparser, logging, json, re
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
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

def extract_json(text):
    """Finds JSON anywhere in the AI's response."""
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
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
            domain = f.url.split('//')[-1].split('/')[0].replace('www.','')
            news[f.name] = {"logo": f"https://img.logo.dev/{domain}?token={token}", "articles": articles}
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
    
    if not key:
        return jsonify({"status": "failed", "reason": "No API Key"})

    try:
        # Strict instructions for the AI
        prompt = f"Find a valid RSS feed URL for {topic}. Output ONLY a JSON object: {{\"n\": \"Site Name\", \"u\": \"https://rss-url.xml\"}}"
        
        # Added required OpenRouter headers (HTTP-Referer and X-Title)
        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://kaivor-news.onrender.com",
            "X-Title": "Kaivor Intelligence",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1 # Low temp = more focused JSON
        }

        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=15)
        raw_data = res.json()
        
        # Debugging: Print to Render logs
        logger.info(f"Agent Raw Response: {raw_data}")

        if 'choices' in raw_data:
            content = raw_data['choices'][0]['message']['content']
            parsed = extract_json(content)
            
            if parsed and 'u' in parsed:
                # Add to DB
                if not Feed.query.filter_by(url=parsed['u']).first():
                    db.session.add(Feed(name=parsed['n'], url=parsed['u']))
                    db.session.commit()
                    return jsonify({"status": "success", "name": parsed['n']})
                return jsonify({"status": "exists"})
                
        return jsonify({"status": "failed", "reason": "No valid URL in AI response"})

    except Exception as e:
        logger.error(f"Agent System Error: {e}")
        return jsonify({"status": "failed", "reason": str(e)})

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
        res = ai.generate_content(f"In 15 words, why is this important: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "Briefing failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
