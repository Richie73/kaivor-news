import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime

# --- LOGGING & APP SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_SYSTEM")
app = Flask(__name__, template_folder='app/templates')

# --- STABLE DATABASE LOGIC ---
def get_db_uri():
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        # quote_plus handles special characters in your password perfectly
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:5432/{n or 'postgres'}?sslmode=require"
    return "sqlite:///kaivor_vault.db"

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- PRODUCTION DATA MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    feed_url = db.Column(db.String(500), unique=True)
    category = db.Column(db.String(50), default='General')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- THE "LIGHTWEIGHT" AI LOGIC ---
def ask_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return "AI Key Missing."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        res = requests.post(url, json={"contents": [{"parts":[{"text": prompt}]}]}, timeout=10).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except: return "AI Service busy."

# --- ROUTES ---
@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except: return jsonify({"status": "unhealthy"}), 500

@app.route('/')
def index():
    # This renders the existing UI you liked
    bookmarks = db.session.query(Article).join(Library).all()
    return render_template('index.html', intel={}, market=[], bookmarks=bookmarks, status="STABLE")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
