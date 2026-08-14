import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from urllib.parse import quote_plus
from datetime import datetime
import google.generativeai as genai

# --- SYSTEM LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_REPAIR_ST1")
app = Flask(__name__, template_folder='app/templates')

# --- FORCED DATABASE LOGIC (BYPASSING RENDER DEFAULTS) ---
def get_db_uri():
    # We look for your individual DB_ boxes first to force the 6543 port
    u = os.environ.get('DB_USER')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME')
    # Force 6543 if we are on Render, otherwise use default
    port = '6543' if 'RENDER' in os.environ else os.environ.get('DB_PORT', '5432')
    
    if all([u, p, h]):
        logger.info(f"Connecting to Cloud DB on Port {port}...")
        pw = quote_plus(p)
        return f"postgresql+psycopg2://{u}:{pw}@{h}:{port}/{n}?sslmode=require"
    
    logger.warning("No Cloud DB variables found. Using local fallback.")
    return 'sqlite:///kaivor_permanent.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODELS ---
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    categories = db.Column(db.String(200))
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    is_saved = db.Column(db.Boolean, default=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- RESILIENT BOOT ---
# This wrapper prevents the "Internal Server Error" if the DB fails
with app.app_context():
    try:
        db.create_all()
        SYSTEM_STATUS = "CONNECTED"
    except Exception as e:
        logger.error(f"DB CONNECTION FAILED: {e}")
        SYSTEM_STATUS = "OFFLINE"

# --- ROUTES ---
@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": "Database unreachable on Port 6543"}), 500

@app.route('/')
def index():
    # If the database is offline, show an empty list instead of crashing
    try:
        saved = db.session.query(Article).join(Library).all()
    except:
        saved = []
    
    # Existing UI needs this data
    matrix = {"UK": [], "Markets": [], "Sport": [], "Tech": [], "Culture": []}
    return render_template('index.html', matrix=matrix, saved=saved, status=SYSTEM_STATUS)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
