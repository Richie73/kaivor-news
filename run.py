import os, requests, feedparser, logging, json, re, hashlib
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from urllib.parse import quote_plus

# --- SYSTEM SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAIVOR_CORE")
app = Flask(__name__, template_folder='app/templates')

# --- DATABASE CONFIG ---
DATABASE_URL = os.environ.get('DATABASE_URL')
def get_db_uri():
    if DATABASE_URL:
        return DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return 'sqlite:///kaivor_dev.db'

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
    category = db.Column(db.String(50))
    enabled = db.Column(db.Boolean, default=True)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    content_hash = db.Column(db.String(64), unique=True) # FINGERPRINT
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)

class Library(db.Model):
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- THE INGESTION ROBOT (DEDUPLICATION) ---
def ingest_feed(url, category_name, source_display_name):
    try:
        h = {'User-Agent': 'Mozilla/5.0 KaivorIntelligence/2.0'}
        r = requests.get(url, headers=h, timeout=10)
        p = feedparser.parse(r.content)
        
        new_count = 0
        for e in p.entries[:10]:
            # Create a unique fingerprint for this article
            fingerprint = hashlib.sha256(e.link.encode()).hexdigest()
            
            # CHECK FOR DUPLICATES
            exists = Article.query.filter_by(content_hash=fingerprint).first()
            if not exists:
                img = e.get('media_thumbnail', [{}])[0].get('url') or e.get('media_content', [{}])[0].get('url')
                new_art = Article(
                    title=e.title,
                    article_url=e.link,
                    image_url=img,
                    source_name=source_display_name,
                    category=category_name,
                    content_hash=fingerprint
                )
                db.session.add(new_art)
                new_count += 1
        db.session.commit()
        return new_count
    except Exception as err:
        logger.error(f"Failed to ingest {source_display_name}: {err}")
        return 0

# --- ROUTES ---
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "database": "connected"}), 200

@app.route('/')
def index():
    # Fetch Articles from DB grouped by your A-F categories
    categories = ["UK", "World", "Markets", "Sport", "Tech", "Culture"]
    matrix = {}
    for cat in categories:
        matrix[cat] = Article.query.filter_by(category=cat).order_by(Article.imported_at.desc()).limit(5).all()
    
    saved = db.session.query(Article).join(Library).all()
    return render_template('index.html', matrix=matrix, saved=saved, status="STABLE")

@app.route('/intel/sync')
def sync():
    # Manual trigger to run the robot
    c1 = ingest_feed("https://feeds.bbci.co.uk/news/uk/rss.xml", "UK", "BBC")
    c2 = ingest_feed("https://feeds.bbci.co.uk/news/world/rss.xml", "World", "BBC")
    c3 = ingest_feed("https://search.cnbc.com/rs/search/view.xml?partnerId=2000&keywords=finance", "Markets", "CNBC")
    c4 = ingest_feed("https://feeds.bbci.co.uk/sport/football/rss.xml", "Sport", "BBC Sport")
    c5 = ingest_feed("https://www.theverge.com/rss/index.xml", "Tech", "The Verge")
    c6 = ingest_feed("https://www.nme.com/news/music/feed", "Culture", "NME")
    return jsonify({"status": "Sync Complete", "new_articles": c1+c2+c3+c4+c5+c6})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
