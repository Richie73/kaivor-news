from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website_url = db.Column(db.String(500))
    feed_url = db.Column(db.String(500), unique=True)
    source_type = db.Column(db.String(20), default='RSS') # RSS, Atom, JSON_API
    enabled = db.Column(db.Boolean, default=True)
    category = db.Column(db.String(50))
    last_successful_import = db.Column(db.DateTime)
    
class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('sources.id'))
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    article_url = db.Column(db.String(500), unique=True)
    image_url = db.Column(db.String(500))
    published_at = db.Column(db.DateTime)
    hash = db.Column(db.String(64), unique=True) # For Deduplication
    is_favourite = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
