import os
import requests
import feedparser
import logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

# Setup logging so we can see errors in Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- DATABASE SETUP ---
# Fix for Render/Supabase connection strings
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///news.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Add SSL requirement for Supabase if using Postgres
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI SETUP ---
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

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

# Initialize Database
try:
    with app.app_context():
        db.create_all()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

@app.route('/')
def index():
    try:
        feeds = Feed.query.all()
        saved = Saved.query.order_by(Saved.id.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching from DB: {e}")
        return f"Database Error: {e}", 500

    news_grouped = {}
    
    # Guardian Trending
    g_key = os.environ.get('GUARDIAN_API_KEY')
    if g_key:
        try:
            g_url = f"https://content.guardianapis.com/search?api-key={g_key}&show-fields=thumbnail&page-size=10"
            res = requests.get(g_url).json()
            if 'response' in res:
                news_grouped['World Trending'] = [{
                    'title': r['webTitle'], 
                    'link': r['webUrl'],
                    'img': r.get('fields', {}).get('thumbnail', '')
                } for r in res['response']['results']]
        except Exception as e:
            logger.warning(f"Guardian API failed: {e}")

    # RSS Feeds
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed.url)
            news_grouped[feed.name] = [{
                'title': e.title, 
                'link': e.link,
                'img': None
            } for e in parsed.entries[:6]]
        except Exception as e:
            logger.warning(f"Failed to parse {feed.name}: {e}")
            
    return render_template('index.html', news_grouped=news_grouped, feeds=feeds, saved=saved)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    if ai_model:
        try:
            prompt = f"In one short sentence, explain why this matters: {title}"
            response = ai_model.generate_content(prompt)
            return jsonify({"summary": response.text})
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
    return jsonify({"summary": "Summary unavailable."})

@app.route('/add', methods=['POST'])
def add_feed():
    name, url = request.form.get('name'), request.form.get('url')
    if name and url:
        db.session.add(Feed(name=name, url=url))
        db.session.commit()
    return redirect('/')

@app.route('/save', methods=['POST'])
def save_article():
    data = request.json
    db.session.add(Saved(title=data['title'], link=data['link'], source=data['source']))
    db.session.commit()
    return jsonify({"status": "success"})

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
