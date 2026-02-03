from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.item_category import generate_custom_id


class ExpenseCategory(Base):
    """Expense categories (bike repair, bills, bilty, commetti, loan, etc.) - separate from item categories."""
    __tablename__ = "expense_categories"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("EXPCAT"))
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    """Daily expense entry: amount, account, category, description; user optional; date defaults to today."""
    __tablename__ = "expenses"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("EXP"))
    date = Column(Date, nullable=False, server_default=func.current_date())
    amount = Column(Numeric(15, 2), nullable=False)
    name = Column(String(100), nullable=False)
    account_id = Column(String(20), ForeignKey("payment_accounts.id"), nullable=False)
    expense_category_id = Column(String(20), ForeignKey("expense_categories.id"), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("PaymentAccount", back_populates="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")
    user = relationship("User", back_populates="expenses")
    ledger_entry = relationship("FinancialLedger", back_populates="expense", uselist=False)
