from datetime import datetime
import uuid
from app import db
from sqlalchemy import Enum
import enum

class PaymentStatus(enum.Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"

class Sale(db.Model):
    __tablename__ = 'sales'
    sale_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = db.Column(db.String(36), db.ForeignKey('items.item_id'))
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.customer_id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    total_amount = db.Column(db.Float)
    payment_status = db.Column(Enum(PaymentStatus))
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    # relationships
    payment = db.relationship('Payment', back_populates='sale', uselist=False)
    item = db.relationship('Item', backref='sales', lazy=True)
    customer = db.relationship('Customer', backref='sales', lazy=True)