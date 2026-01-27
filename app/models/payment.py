import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.item_category import generate_custom_id


class PaymentAccountType(str,enum.Enum):
    CASH = "CASH"
    BANK = "BANK"
    JAZZCASH = "JAZZCASH"
    EASYPAISA = "EASYPAISA"

class PaymentType(str, enum.Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    UN_PAID = "UN_PAID"

class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("ACC"))
    name = Column(String(50), nullable=False) 
    type = Column(Enum(PaymentAccountType),nullable=False) # Cash, Bank, JazzCash 

    created_at = Column(DateTime, server_default=func.now())
    payments = relationship("Payment", back_populates="accounts")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("PAY"))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purchase_invoice_id = Column(String(30), ForeignKey("purchase_invoices.id"), nullable=True)
    sale_invoice_id = Column(String(30), ForeignKey("sale_invoices.id"), nullable=True) 

    amount = Column(Numeric(15,2), nullable=False)
    account_id = Column(String(20), ForeignKey("payment_accounts.id"))
    payment_type = Column(Enum(PaymentType), nullable=False) 
    created_at = Column(DateTime, server_default=func.now())

    purchase_invoice = relationship("PurchaseInvoice", back_populates="payments")
    sale_invoice = relationship("SaleInvoice", back_populates="payments")

    user = relationship("User", back_populates="payment")
    account = relationship("PaymentAccount", back_populates="payments")
