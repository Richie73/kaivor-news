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
    name = db.Column(db.String(100)); url = db.Column(db.String(500)); category = db.Column(db.String(50), default='Intelligence')

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
    categories = set(['Intelligence', 'Markets', 'Technology'])
    
    # 1. NEWSDATA.IO
    nd_key = os.environ.get('NEWSDATA_KEY')
    if nd_key:
        try:
            r = requests.get(f"https://newsdata.io/api/1/latest?apikey={nd_key}&country=gb,us&language=en&category=top&image=1", timeout=5).json()
            if 'results' in r:
                news['Breaking'] = {"cat": "Intelligence", "logo": "https://cdn-icons-png.flaticon.com/512/21/21601.png",
                    "articles": [{'title': a['title'], 'link': a['link'], 'img': a.get('image_url')} for a in r['results'][:5]]}
        except: pass

    # 2. GUARDIAN & NYT
    g_key, nyt_key = os.environ.get('GUARDIAN_API_KEY'), os.environ.get('NYT_API_KEY')
    if g_key:
        try:
            r = requests.get(f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail").json()
            news['Guardian'] = {"cat": "Intelligence", "logo": "https://img.logo.dev/theguardian.com?token="+os.environ.get('LOGODEV_TOKEN',''),
                "articles": [{'title': a['webTitle'], 'link': a['webUrl'], 'img': a.get('fields',{}).get('thumbnail')} for a in r['response']['results'][:5]]}
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
            categories.add(f.category)
        except: continue

    return render_template('index.html', news=news, bookmarks=bookmarks, feeds=feeds, categories=sorted(list(categories)))

@app.route('/summarize', methods=['POST'])
def summarize():
    t = request.json.get('title')
    try:
        res = ai.generate_content(f"In 15 words: {t}")
        return jsonify({"summary": res.text})
    except: return jsonify({"summary": "AI connection busy."})

@app.route('/bookmark', methods=['POST'])
def save_bookmark():
    d = request.json
    db.session.add(Bookmark(title=d['title'], link=d['link'], img=d['img'], source=d['source'])); db.session.commit()
    return jsonify({"status": "success"})

@app.route('/auto-add', methods=['POST'])
def auto_add():
    topic = request.json.get('topic'); key = os.environ.get('OPENROUTER_API_KEY')
    try:
        prompt = f"Official RSS for {topic}. JSON: {{\"n\": \"Name\", \"u\": \"URL\", \"c\": \"Category\"}}"
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
