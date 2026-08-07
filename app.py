import os
import requests
import feedparser
import logging
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse, quote_plus
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- AUTOMATIC DATABASE CLEANER ---
def get_clean_db_url():
    url = os.environ.get('DATABASE_URL', '').strip()
    
    # If no URL, use local storage
    if not url:
        return 'sqlite:///news.db'
    
    try:
        # Standardize prefix for SQLAlchemy
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # Ensure SSL for Supabase
        if "sslmode" not in url:
            sep = "&" if "?" in url else "?"
            url += f"{sep}sslmode=require"
            
        return url
    except Exception as e:
        logger.error(f"URL Cleaning failed: {e}")
        return 'sqlite:///news.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_clean_db_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

# Safety check for DB initialization
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        logger.error(f"Database Error: {e}")

# AI Setup
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
    weather = {"temp": "--", "desc": "..."}
    market = []
    
    # Weather
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric").json()
            weather = {"temp": int(w_res['main']['temp']), "desc": w_res['weather'][0]['main']}
        except: pass

    # News & Market Logic
    logo_token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            parsed = feedparser.parse(f.url)
            domain = urlparse(f.url).netloc.replace('feeds.', '').replace('www.', '')
            news_grouped[f.name] = {
                "logo": f"https://img.logo.dev/{domain}?token={logo_token}",
                "articles": [{'title': e.title, 'link': e.link} for e in parsed.entries[:5]]
            }
        except: continue

    return render_template('index.html', news_grouped=news_grouped, weather=weather, market=market, saved=saved)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    if ai_model:
        try:
            response = ai_model.generate_content(f"Significance in 1 short sentence: {title}")
            return jsonify({"summary": response.text})
        except: pass
    return jsonify({"summary": "Brief unavailable."})

@app.route('/add', methods=['POST'])
def add_feed():
    n, u = request.form.get('name'), request.form.get('url')
    if n and u:
        db.session.add(Feed(name=n, url=u))
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
