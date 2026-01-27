
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class FinancialLedger(Base):
    __tablename__ = "financial_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    ref_type = Column(String(20))   # PURCHASE / SALE / PAYMENT
    ref_id = Column(String(30))     # PINV / SINV / PAY

    debit = Column(Numeric(15,2), default=0)
    credit = Column(Numeric(15,2), default=0)

    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates='ledger_entries')
