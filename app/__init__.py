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

    from app.routes.customers import customer_bp
    app.register_blueprint(customer_bp, url_prefix="/api/customers")

    from app.routes.purchase_item import purchase_bp
    app.register_blueprint(purchase_bp, url_prefix="/api/purchases")

    from app.routes.stocks import stocks_bp
    app.register_blueprint(stocks_bp, url_prefix="/api/stocks")

    from app.routes.items import items_bp 
    app.register_blueprint(items_bp, url_prefix="/api/items")

    from app.routes.payments import payment_bp 
    app.register_blueprint(payment_bp, url_prefix="/api/payments")



    register_error_handlers(app)

    return app

