from flask import Flask
from app.models.news import db
from urllib.parse import quote_plus
import os

def create_app():
    app = Flask(__name__)
    
    # Secure DB Connection using your split variables
    u = os.environ.get('DB_USER')
    p = os.environ.get('DB_PASSWORD')
    h = os.environ.get('DB_HOST')
    n = os.environ.get('DB_NAME')
    
    if all([u, p, h]):
        # Port 6543 is the critical fix for Render Network Unreachable errors
        uri = f"postgresql+psycopg2://{u}:{quote_plus(p)}@{h}:6543/{n}?sslmode=require"
    else:
        uri = "sqlite:///kaivor_dev.db"

    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
    # Register Blueprints (Routes)
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app
