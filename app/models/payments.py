from datetime import datetime
import uuid
from app import db
import enum
from sqlalchemy import Enum

class PaymentMethod(enum.Enum):
    CASH = "Cash"
    BANK = "Bank"

class BankAccounts(enum.Enum):
    MEEZAN = "Meezan Bank"
    HBL = "Habib Bank Limited"
    UBL = "United Bank Limited"

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purchase_id = db.Column(db.String(36), db.ForeignKey('purchases.purchase_id'))
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.sale_id'))
    method = db.Column(Enum(PaymentMethod))
    bank_account = db.Column(Enum(BankAccounts), nullable=True)
    amount_paid = db.Column(db.Float)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)

     # 🔁 Relationships (optional but useful)
    purchase = db.relationship('Purchase', back_populates='payment', uselist=False)
    sale = db.relationship('Sale', back_populates='payment', uselist=False)
 