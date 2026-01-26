import enum
import secrets
import string
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ItemType(str, enum.Enum):
    final_product = "final_product"
    raw_material = "raw_material"


class UnitType(str, enum.Enum):
    PCS = "PCS"
    SET = "SET"


@staticmethod
def generate_custom_id(prefix: str, length: int = 8) -> str:
    random_part = ''.join(secrets.choice(string.ascii_uppercase)
                          for _ in range(length))
    return f"{prefix}-{random_part}"


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(15), primary_key=True,
                default=lambda: generate_custom_id("CAT"))
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    items = relationship("Item", back_populates="category")


class Item(Base):
    __tablename__ = "items"

    id = Column(String(15), primary_key=True,
                default=lambda: generate_custom_id("ITM"))
    name = Column(String(100), nullable=False)
    type = Column(Enum(ItemType), nullable=False)
    unit_type = Column(Enum(UnitType), nullable=False)

    avg_price = Column(Numeric(15, 2), default=0)
    total_quantity = Column(Integer, default=0)

    category_id = Column(String(20), ForeignKey(
        "categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="items")
    # stock_records = relationship("Stock", back_populates="item")
    # sale_records = relationship("Sale", back_populates="item")
