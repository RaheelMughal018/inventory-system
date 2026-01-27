import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models import payment
from app.models.item_category import generate_custom_id


class InvoiceStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
class Stock(Base):
    __tablename__ = "stock_ledger"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("STK"))

    item_id = Column(String(10), ForeignKey("items.id"), nullable=False)

    ref_type = Column(String(20))  # PURCHASE / SALE / ADJUSTMENT
    ref_id = Column(String(30)) # PINV/SINV

    qty_in = Column(Integer,default=0)
    qty_out = Column(Integer,default=0)

    unit_price = Column(Numeric(15,2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item", back_populates="stock_entries")
class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("PINV"))
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_amount = Column(Numeric(15,2), nullable=False)
    paid_amount = Column(Numeric(15,2), default=0.00)
    balance_due = Column(Numeric(15,2), nullable=False) # total - paid = due
    payment_status = Column(Enum(InvoiceStatus), default=InvoiceStatus.UNPAID)  
    
    created_at = Column(DateTime, server_default=func.now())

    supplier = relationship("User")
    items = relationship("PurchaseItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="purchase_invoice", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(String(30), ForeignKey("purchase_invoices.id"))

    item_id = Column(String(10), ForeignKey("items.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)

    invoice = relationship("PurchaseInvoice", back_populates="items")
    item = relationship("Item")


class SaleInvoice(Base):
    __tablename__ = "sale_invoices"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("SINV"))
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_amount = Column(Numeric(15,2), nullable=False)
    recieved_amount = Column(Numeric(15,2), default=0.00)
    balance_due = Column(Numeric(15,2), nullable=False)

    payment_status = Column(Enum(InvoiceStatus), default=InvoiceStatus.UNPAID)  

    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("User")
    items = relationship("SaleItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale_invoice", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(String(30), ForeignKey("sale_invoices.id"))

    item_id = Column(String(10), ForeignKey("items.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)

    invoice = relationship("SaleInvoice", back_populates="items")
    item = relationship("Item")


