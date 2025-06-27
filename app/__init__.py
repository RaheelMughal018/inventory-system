from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from .common.error_handlers import register_error_handlers
from app.common.logger import setup_logger

# Initialize extensions globally
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # setup logging
    setup_logger(app)

   # Register route blueprints
    from app.routes.suppliers import supplier_bp
    app.register_blueprint(supplier_bp, url_prefix="/api/suppliers")


    register_error_handlers(app)

    return app

