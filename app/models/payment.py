import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.item_category import generate_custom_id


class PaymentAccountType(str, enum.Enum):
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
    type = Column(Enum(PaymentAccountType), nullable=False)  # Cash, Bank, JazzCash
    opening_balance = Column(Numeric(15, 2), nullable=True, default=0)

    created_at = Column(DateTime, server_default=func.now())
    payments = relationship("Payment", back_populates="account")
    expenses = relationship("Expense", back_populates="account")
    ledger_entries = relationship("AccountLedger", back_populates="account", cascade="all, delete-orphan")


class AccountLedger(Base):
    """
    Ledger for each payment account: every in/out flow.
    - credit = money in (opening balance, sale payment received)
    - debit = money out (supplier payment, purchase payment, expense)
    Balance = opening_balance + sum(credits) - sum(debits) from this table,
    or equivalently sum(credit) - sum(debit) if opening is stored as first ledger row.
    """
    __tablename__ = "account_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(20), ForeignKey("payment_accounts.id", ondelete="CASCADE"), nullable=False)

    ref_type = Column(String(30), nullable=False)  # OPENING_BALANCE, PAYMENT_SUPPLIER, PAYMENT_PURCHASE, PAYMENT_SALE, EXPENSE
    ref_id = Column(String(50), nullable=True)  # payment id, invoice id, expense id

    debit = Column(Numeric(15, 2), default=0, nullable=False)
    credit = Column(Numeric(15, 2), default=0, nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    account = relationship("PaymentAccount", back_populates="ledger_entries")


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
