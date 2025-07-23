from datetime import datetime
import uuid
from app import db
import enum
from sqlalchemy import Enum

class PaymentMethod(enum.Enum):
    CASH = "Cash"
    BANK = "Bank"

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purchase_id = db.Column(db.String(36), db.ForeignKey('purchases.purchase_id'))
    method = db.Column(Enum(PaymentMethod))
    bank_account = db.Column(db.String(100), nullable=True)
    amount_paid = db.Column(db.Float)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)