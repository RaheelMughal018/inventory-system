from sqlalchemy import Column, Enum, ForeignKey, Integer, String, DateTime, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import secrets
import string
from app.core.database import Base
from app.models import payment


class UserRole(str, enum.Enum):
    owner = "owner"
    supplier = "supplier"
    customer = "customer"


class User(Base):  
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), unique=True, nullable=False, index=True)  
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.supplier)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Self-referential FK -> who created this user 
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    
    # Relationships
    creator = relationship("User", remote_side=[id], backref="users_created") 
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ledger_entries = relationship("FinancialLedger", back_populates="user", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="user")

    @staticmethod
    def generate_user_id(role: UserRole) -> str:
        """Generate a short unique user ID based on role"""
        prefix = {
            UserRole.owner: "OWN",
            UserRole.supplier: "SUP",
            UserRole.customer: "CUS"
        }[role]
        
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                             for _ in range(8))
        
        return f"{prefix}-{random_part}"

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}')>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic profile info (common for all users)
    profile_picture = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    # Business/Company details (for suppliers and customers)
    company_name = Column(String(255), nullable=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)  
    user = relationship("User", back_populates="profile")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, company='{self.company_name}')>"
    
    @property
    def is_supplier(self):
        """Check if this profile belongs to a supplier"""
        return self.user.role == UserRole.supplier
    
    @property
    def is_customer(self):
        """Check if this profile belongs to a customer"""
        return self.user.role == UserRole.customer
    
    @property
    def balance_due(self):
        """Calculate balance due from financial ledger entries"""
        # This should be calculated from FinancialLedger entries
        # For now, return 0.00 - implement calculation in service layer
        return 0.00