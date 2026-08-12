from flask import Blueprint, render_template, request, jsonify
from app.models.news import Article, Source, db
from app.services.ingestion import IngestionService

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    articles = Article.query.order_by(Article.published_at.desc()).all()
    sources = Source.query.all()
    return render_template('index.html', articles=articles, sources=sources)

@bp.route('/discover', methods=['POST'])
def discover():
    query = request.form.get('query')
    # Discovery Logic Triggered here
    return render_template('components/discovery_results.html', query=query)

@bp.route('/bookmark/<int:id>', methods=['POST'])
def bookmark(id):
    art = Article.query.get(id)
    art.is_favourite = not art.is_favourite
    db.session.commit()
    return "" # HTMX handles UI update
