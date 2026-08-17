from run import app, db, Article, Source
from sqlalchemy import text

def map_data():
    with app.app_context():
        print("Starting Data Mapping...")
        articles = Article.query.filter(Article.source_id == None).all()
        mapped = 0
        for art in articles:
            # Try to match the legacy string 'source_name' to a Source record
            src = Source.query.filter_by(name=art.source_name).first()
            if src:
                art.source_id = src.id
                mapped += 1
        db.session.commit()
        print(f"Mapping Complete. {mapped} articles linked to sources.")

if __name__ == "__main__":
    map_data()
