import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_PROD")
app = Flask(__name__, template_folder='app/templates')

# --- PRODUCTION DATABASE LOGIC ---
# This now looks for the IPv4-friendly Neon/Render URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_uri():
    if DATABASE_URL:
        # Fix for Render legacy strings
        uri = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return uri
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

# Sync Database Tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database synchronized.")
    except Exception as e:
        logger.error(f"Sync error: {e}")

# --- ROUTES ---
@app.route('/health')
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def index():
    try:
        saved = db.session.query(Article).join(Library).all()
        status = "CONNECTED"
    except:
        saved = []
        status = "OFFLINE"
    
    market = [{"s": "BTC", "v": "$64,210"}, {"s": "GOLD", "v": "$2,458"}]
    return render_template('index.html', intel={}, market=market, bookmarks=saved, status=status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
