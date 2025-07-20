from app import db
from datetime import datetime
import uuid


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # relationship with Item
    item_id = db.Column(db.String(36), db.ForeignKey('items.id'), nullable=False)
    item = db.relationship('Item', back_populates='categories')

   