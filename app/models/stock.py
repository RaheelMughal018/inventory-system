from datetime import datetime
import uuid
from app import db





class Stock(db.Model):
    __tablename__ = 'stock'
    stock_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = db.Column(db.String(36), db.ForeignKey('items.item_id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer,nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
