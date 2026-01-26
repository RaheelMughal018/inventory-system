from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.item_category import generate_custom_id


class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("ACC"))
    name = Column(String(50), nullable=False)  # Cash, Bank, JazzCash
    type = Column(String(20))                  # cash, bank, wallet

    created_at = Column(DateTime, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("PAY"))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_type = Column(String(20))  # PURCHASE / SALE
    invoice_id = Column(String(30))    # PINV / SINV

    amount = Column(Numeric(15,2), nullable=False)
    account_id = Column(String(20), ForeignKey("payment_accounts.id"))

    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
    account = relationship("PaymentAccount")
