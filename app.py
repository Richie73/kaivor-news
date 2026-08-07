import os, requests, feedparser, sqlite3
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
import google.generativeai as genai

app = Flask(__name__)

# Database
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///news.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)

# AI Setup
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
    db.create_all()

def get_domain(url):
    """Turns http://feeds.bbci.co.uk/news into bbc.co.uk"""
    return urlparse(url).netloc.replace('feeds.', '').replace('www.', '')

@app.route('/')
def index():
    feeds = Feed.query.all()
    saved = Saved.query.order_by(Saved.id.desc()).all()
    news_grouped = {}
    
    # 1. Weather logic
    weather = {"temp": "--", "desc": "Loading..."}
    w_key = os.environ.get('WEATHER_KEY')
    if w_key:
        try:
            # Change 'London' to your city
            w_url = f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={w_key}&units=metric"
            res = requests.get(w_url).json()
            weather = {"temp": int(res['main']['temp']), "desc": res['weather'][0]['main']}
        except: pass

    # 2. News Logic
    logo_token = os.environ.get('LOGODEV_TOKEN')
    for f in feeds:
        try:
            parsed = feedparser.parse(f.url)
            domain = get_domain(f.url)
            # Add Logo.dev URL to the source
            logo = f"https://img.logo.dev/{domain}?token={logo_token}"
            news_grouped[f.name] = {
                "logo": logo,
                "articles": [{'title': e.title, 'link': e.link} for e in parsed.entries[:5]]
            }
        except: continue

    return render_template('index.html', news_grouped=news_grouped, weather=weather, saved=saved)

@app.route('/summarize', methods=['POST'])
def summarize():
    title = request.json.get('title')
    try:
        response = ai_model.generate_content(f"Why does this headline matter? {title}")
        return jsonify({"summary": response.text})
    except: return jsonify({"summary": "Error."})

@app.route('/add', methods=['POST'])
def add_feed():
    db.session.add(Feed(name=request.form.get('name'), url=request.form.get('url')))
    db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
