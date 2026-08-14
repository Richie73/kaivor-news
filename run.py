import os, requests, feedparser, logging, json, re, hashlib, traceback
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from urllib.parse import quote_plus

# --- SYSTEM SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_RESCUE")
app = Flask(__name__, template_folder='app/templates')

# --- STABLE DATABASE LOGIC ---
def get_db_uri():
    # Priority 1: Use split variables (Most stable for your password)
    u, p, h, n = os.environ.get('DB_USER'), os.environ.get('DB_PASSWORD'), os.environ.get('DB_HOST'), os.environ.get('DB_NAME')
    if all([u, p, h]):
        return f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n or 'postgres'}?sslmode=require"
    
    # Priority 2: Use direct URL
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri.replace("postgres://", "postgresql://", 1)
        
    return 'sqlite:///kaivor_emergency.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- PRODUCTION MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(50), default='General')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    content_hash = db.Column(db.String(64), unique=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# Ensure database is synced on start
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        logger.error(f"Startup DB Error: {e}")

# --- RECOVERY LOGIC ---
@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def index():
    try:
        # A-F CATEGORY LOGIC
        categories = ["UK", "World", "Markets", "Sport", "Tech", "Culture"]
        matrix = {}
        for cat in categories:
            # Note: Using .all() to ensure we get results for the UI
            matrix[cat] = Article.query.filter_by(category=cat).order_by(Article.imported_at.desc()).limit(5).all()
        
        saved = db.session.query(Article).join(Library).all()
        
        # Placeholder Market Data
        market = [{"s": "BTC", "v": "$64,210"}, {"s": "GOLD", "v": "$2,458"}]
        
        return render_template('index.html', matrix=matrix, saved=saved, status="CONNECTED")
    
    except Exception as e:
        # DEBUG SHIELD: Instead of a 500 error, show the exact problem on screen
        error_info = traceback.format_exc()
        return f"<html><body style='background:#000;color:red;padding:20px;font-family:monospace;'><h1>KAIVOR BOOT ERROR</h1><p>{str(e)}</p><pre>{error_info}</pre></body></html>", 500

@app.route('/intel/sync')
def sync():
    # For now, a simple successful response to verify the route exists
    return jsonify({"status": "Sync engine active. Please use /intel/sync to fetch."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
