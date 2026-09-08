import os
import requests
import feedparser
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///news.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
db = SQLAlchemy(app)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    url = db.Column(db.String(500))

class Saved(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500))
    link = db.Column(db.String(500))
    source = db.Column(db.String(100))

with app.app_context():
    try:
        db.create_all()
    except:
        pass

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
    except:
        feeds = []

    try:
        saved = Saved.query.order_by(Saved.id.desc()).all()
    except:
        saved = []

    news_grouped = {}
    
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10"
            res = requests.get(g_url).json()
            news_grouped['World Trending'] = [{
                'title': r['webTitle'], 
                'link': r['webUrl'],
                'img': r.get('fields', {}).get('thumbnail', '')
            } for r in res['response']['results']]
        except: pass

    # Robust Markets Feed with forced [$] currency symbols
    try:
        market_parsed = feedparser.parse("https://www.cnbc.com/id/10000664/device/rss/rss.html")
        items = []
        for e in market_parsed.entries[:6]:
            t = e.title if hasattr(e, 'title') else "Market Update"
            if not t.startswith("[$]"):
                t = f"[$] {t}"
            items.append({'title': t, 'link': e.link, 'img': None})
        news_grouped['Markets'] = items
    except: 
        news_grouped['Markets'] = [{'title': '[$] Market data temporarily unavailable', 'link': '#', 'img': None}]

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed.url)
            news_grouped[feed.name] = [{
                'title': f"[$] {e.title}" if not e.title.startswith("[$]") else e.title,
                'link': e.link,
                'img': None
            } for e in parsed.entries[:6]]
        except: continue
            
    return render_template('index.html', news_grouped=news_grouped, feeds=feeds, saved=saved)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    try:
        prompt = f"In one short, punchy sentence, explain the importance of this news: {title}"
        response = ai_model.generate_content(prompt)
        return jsonify({"summary": response.text})
    except:
        return jsonify({"summary": "Briefing unavailable."})

@app.route('/add', methods=['POST'])
def add_feed():
    name, url = request.form.get('name'), request.form.get('url')
    if name and url:
        try:
            db.session.add(Feed(name=name, url=url))
            db.session.commit()
        except:
            db.session.rollback()
    return redirect('/')

@app.route('/save', methods=['POST'])
def save_article():
    data = request.json
    try:
        db.session.add(Saved(title=data['title'], link=data['link'], source=data['source']))
        db.session.commit()
        return jsonify({"status": "success"})
    except:
        db.session.rollback()
        return jsonify({"status": "error"}), 500

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    try:
        f = Feed.query.get(id)
        if f:
            db.session.delete(f)
            db.session.commit()
    except:
        db.session.rollback()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
