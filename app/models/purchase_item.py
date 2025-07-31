from datetime import datetime
import uuid
from app import db
from sqlalchemy import Enum
import enum

class PaymentStatus(enum.Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"

class Purchase(db.Model):
    __tablename__ = 'purchases'
    purchase_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = db.Column(db.String(36), db.ForeignKey('items.item_id'))
    supplier_id = db.Column(db.String(36), db.ForeignKey('suppliers.supplier_id'))
    quantity = db.Column(db.Integer)
    total_amount = db.Column(db.Float)
    payment_status = db.Column(Enum(PaymentStatus))
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    # relationships
    payment = db.relationship('Payment', back_populates='purchase', uselist=False)
    item = db.relationship('Item', backref='purchases', lazy=True)
    supplier = db.relationship('Supplier', backref='purchases', lazy=True)