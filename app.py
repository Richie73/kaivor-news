import os
import requests
import feedparser
import logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- DATABASE LOGIC ---
def get_db_url():
    raw_url = os.environ.get('DATABASE_URL', '').strip()
    
    if not raw_url:
        logger.info("DATABASE_URL is empty. Using local SQLite.")
        return 'sqlite:///news.db'
    
    # Fix 'postgres://' to 'postgresql://' (Required by SQLAlchemy)
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    
    # Add SSL mode for Supabase/Cloud providers
    if "postgresql" in raw_url and "sslmode" not in raw_url:
        sep = "&" if "?" in raw_url else "?"
        raw_url += f"{sep}sslmode=require"
    
    return raw_url

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Try to initialize SQLAlchemy without crashing
try:
    db = SQLAlchemy(app)
except Exception as e:
    logger.error(f"SQLAlchemy Init Failed: {e}")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'
    db = SQLAlchemy(app)

# --- MODELS ---
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
    except Exception as e:
        logger.error(f"Table Creation Failed: {e}")

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
        saved = Saved.query.order_by(Saved.id.desc()).all()
    except:
        feeds, saved = [], []
    
    news_grouped = {}
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10"
            res = requests.get(g_url).json()
            if 'response' in res:
                news_grouped['World Trending'] = [{
                    'title': r['webTitle'], 'link': r['webUrl'],
                    'img': r.get('fields', {}).get('thumbnail', '')
                } for r in res['response']['results']]
        except: pass

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed.url)
            news_grouped[feed.name] = [{
                'title': e.title, 'link': e.link, 'img': None
            } for e in parsed.entries[:6]]
        except: continue
            
    return render_template('index.html', news_grouped=news_grouped, feeds=feeds, saved=saved)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    if ai_model:
        try:
            response = ai_model.generate_content(f"Summarize this news headline in 1 short sentence: {title}")
            return jsonify({"summary": response.text})
        except: pass
    return jsonify({"summary": "Brief unavailable."})

@app.route('/add', methods=['POST'])
def add_feed():
    name, url = request.form.get('name'), request.form.get('url')
    if name and url:
        db.session.add(Feed(name=name, url=url))
        db.session.commit()
    return redirect('/')

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    f = Feed.query.get(id)
    if f:
        db.session.delete(f)
        db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
