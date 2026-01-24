from sqlalchemy import Column, Enum, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import secrets
import string
from app.core.database import Base


class UserRole(str, enum.Enum):
    owner = "owner"
    supplier = "supplier"
    customer = "customer"


class User(Base):  
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), unique=True, nullable=False, index=True)  
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.supplier)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Self-referential FK -> who created this user 
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    
    # Relationships
    creator = relationship("User", remote_side=[id], backref="users_created") 
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

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
    profile_picture = Column(String(500), nullable=True)

    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)  
    user = relationship("User", back_populates="profile")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id})>"