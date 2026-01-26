from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.item_category import generate_custom_id


class Stock(Base):
    __tablename__ = "stock_ledger"

    id = Column(String(20), primary_key=True)

    item_id = Column(String(20), ForeignKey("items.id"), nullable=False)

    ref_type = Column(String(20))  # PURCHASE / SALE / ADJUSTMENT
    ref_id = Column(String(20)) # PINV/SINV

    qty_in = Column(Integer,default=0)
    qty_out = Column(Integer,default=0)

    unit_price = Column(Numeric(15,2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item", back_populates="stock_records")

class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("PINV"))
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_amount = Column(Numeric(15,2), nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    supplier = relationship("User")
    items = relationship("PurchaseItem", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(String(30), ForeignKey("purchase_invoices.id"))

    item_id = Column(String(20), ForeignKey("items.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)

    item = relationship("Item")


class SaleInvoice(Base):
    __tablename__ = "sale_invoices"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("SINV"))
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_amount = Column(Numeric(15,2), nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("User")
    items = relationship("SaleItem", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(String(30), ForeignKey("sale_invoices.id"))

    item_id = Column(String(20), ForeignKey("items.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)

    item = relationship("Item")


