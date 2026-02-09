from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional, List
from decimal import Decimal
from app.models.stock import PurchaseInvoice
from app.models.user import User, UserRole, UserProfile
from app.models.financial_ledger import FinancialLedger
from app.core.security import get_password_hash
from app.logger_config import logger


def get_supplier_by_id(db: Session, supplier_id: int) -> Optional[User]:
    """Get supplier by database ID (must have supplier role)."""
    user = db.query(User).filter(User.id == supplier_id, User.role == UserRole.supplier).first()
    return user


def get_supplier_by_user_id(db: Session, user_id: str) -> Optional[User]:
    """Get supplier by user_id (e.g., 'SUP-ABC12345')."""
    user = db.query(User).filter(User.user_id == user_id, User.role == UserRole.supplier).first()
    return user


def get_supplier_by_email(db: Session, email: str) -> Optional[User]:
    """Get supplier by email (must have supplier role)."""
    user = db.query(User).filter(User.email == email, User.role == UserRole.supplier).first()
    return user


def get_all_suppliers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> tuple[List[User], int]:
    """Get all suppliers with optional search filtering."""
    query = db.query(User).filter(User.role == UserRole.supplier)
    
    if search:
        search_term = f"%{search}%"
        # Use left outer join to include suppliers without profiles
        query = query.outerjoin(UserProfile, User.id == UserProfile.user_id).filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.user_id.ilike(search_term),
                UserProfile.company_name.ilike(search_term)
            )
        )
    
    total = query.count()
    suppliers = query.offset(skip).limit(limit).all()
    
    return suppliers, total


def create_supplier(
    db: Session,
    name: str,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None,
    opening_balance: Optional[Decimal] = None,
    opening_balance_type: Optional[str] = 'DEBIT',
    created_by_id: Optional[int] = None
) -> User:
    """Create a new supplier with optional opening balance.
    
    Args:
        opening_balance_type: 'DEBIT' means you owe the supplier, 'CREDIT' means supplier owes you
    """
    # Generate unique user_id
    user_id = User.generate_user_id(UserRole.supplier)
    
    # Ensure user_id is unique
    while db.query(User).filter(User.user_id == user_id).first():
        user_id = User.generate_user_id(UserRole.supplier)
    
    
    # Create user with supplier role
    user = User(
        user_id=user_id,
        email=None,
        password_hash=None,
        name=name,
        role=UserRole.supplier,
        created_by_id=created_by_id
    )
    
    db.add(user)
    db.flush()  # Flush to get user.id
    
    # Set opening balance to 0 if not provided
    if opening_balance is None:
        opening_balance = Decimal('0.00')
    
    # Set default type if not provided
    if opening_balance_type is None:
        opening_balance_type = 'DEBIT'
    
    # Create user profile with supplier-specific data
    profile = UserProfile(
        user_id=user.id,
        company_name=company_name,
        phone=phone,
        city=city,
        opening_balance=opening_balance,
        opening_balance_type=opening_balance_type
    )
    db.add(profile)
    db.flush()  # Flush to get profile created
    
    # Create financial ledger entry for opening balance if > 0
    if opening_balance > 0:
        if opening_balance_type == 'DEBIT':
            # You owe the supplier (liability)
            debit_amt = opening_balance
            credit_amt = Decimal('0.00')
        else:  # CREDIT
            # Supplier owes you (asset)
            debit_amt = Decimal('0.00')
            credit_amt = opening_balance
        
        ledger_entry = FinancialLedger(
            user_id=user.id,
            ref_type="OPENING_BALANCE",
            ref_id=f"OB-{user.user_id}",
            debit=debit_amt,
            credit=credit_amt
        )
        db.add(ledger_entry)
        logger.info(f"Created opening balance ledger entry: Supplier {user.user_id}, Type: {opening_balance_type}, Amount: {opening_balance}")
    
    try:
        db.commit()
        db.refresh(user)
        db.refresh(profile)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating supplier: {str(e)}")
        raise ValueError("Failed to create supplier. User ID or email may already exist.")


def update_supplier(
    db: Session,
    supplier_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None,
    opening_balance: Optional[Decimal] = None,
    opening_balance_type: Optional[str] = None
) -> Optional[User]:
    """Update supplier information and adjust opening balance if needed.
    
    Args:
        opening_balance_type: 'DEBIT' means you owe the supplier, 'CREDIT' means supplier owes you
    """
    user = get_supplier_by_id(db, supplier_id)
    if not user:
        return None
    
    if name is not None:
        user.name = name
    if email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user and existing_user.id != supplier_id:
            raise ValueError("Email is already taken by another user")
        user.email = email
    
    # Update profile information
    if user.profile:
        old_opening_balance = user.profile.opening_balance or Decimal('0.00')
        old_opening_balance_type = user.profile.opening_balance_type or 'DEBIT'
        
        if company_name is not None:
            user.profile.company_name = company_name
        if phone is not None:
            user.profile.phone = phone
        if city is not None:
            user.profile.city = city
        
        # Handle opening balance or type update
        balance_changed = opening_balance is not None and opening_balance != old_opening_balance
        type_changed = opening_balance_type is not None and opening_balance_type != old_opening_balance_type
        
        if balance_changed or type_changed:
            # Update profile values
            if opening_balance is not None:
                user.profile.opening_balance = opening_balance
            else:
                opening_balance = old_opening_balance
                
            if opening_balance_type is not None:
                user.profile.opening_balance_type = opening_balance_type
            else:
                opening_balance_type = old_opening_balance_type
            
            # Check if there's an existing opening balance ledger entry
            existing_ob_entry = db.query(FinancialLedger).filter(
                FinancialLedger.user_id == supplier_id,
                FinancialLedger.ref_type == "OPENING_BALANCE"
            ).first()
            
            if opening_balance > 0:
                # Determine debit/credit based on type
                if opening_balance_type == 'DEBIT':
                    debit_amt = opening_balance
                    credit_amt = Decimal('0.00')
                else:  # CREDIT
                    debit_amt = Decimal('0.00')
                    credit_amt = opening_balance
                
                if existing_ob_entry:
                    # Update existing entry
                    existing_ob_entry.debit = debit_amt
                    existing_ob_entry.credit = credit_amt
                    logger.info(f"Updated opening balance ledger: Supplier {user.user_id}, Type: {opening_balance_type}, Amount: {opening_balance}")
                else:
                    # Create new opening balance entry
                    ledger_entry = FinancialLedger(
                        user_id=supplier_id,
                        ref_type="OPENING_BALANCE",
                        ref_id=f"OB-{user.user_id}",
                        debit=debit_amt,
                        credit=credit_amt
                    )
                    db.add(ledger_entry)
                    logger.info(f"Created opening balance ledger: Supplier {user.user_id}, Type: {opening_balance_type}, Amount: {opening_balance}")
            elif existing_ob_entry and opening_balance == 0:
                # Remove opening balance entry if set to 0
                db.delete(existing_ob_entry)
                logger.info(f"Removed opening balance ledger: Supplier {user.user_id}")
    else:
        # Create profile if it doesn't exist
        opening_bal = opening_balance if opening_balance is not None else Decimal('0.00')
        opening_bal_type = opening_balance_type if opening_balance_type is not None else 'DEBIT'
        
        profile = UserProfile(
            user_id=user.id,
            company_name=company_name,
            phone=phone,
            city=city,
            opening_balance=opening_bal,
            opening_balance_type=opening_bal_type
        )
        db.add(profile)
        db.flush()
        
        # Create opening balance ledger entry if > 0
        if opening_bal > 0:
            if opening_bal_type == 'DEBIT':
                debit_amt = opening_bal
                credit_amt = Decimal('0.00')
            else:  # CREDIT
                debit_amt = Decimal('0.00')
                credit_amt = opening_bal
                
            ledger_entry = FinancialLedger(
                user_id=supplier_id,
                ref_type="OPENING_BALANCE",
                ref_id=f"OB-{user.user_id}",
                debit=debit_amt,
                credit=credit_amt
            )
            db.add(ledger_entry)
            logger.info(f"Created opening balance ledger: Supplier {user.user_id}, Type: {opening_bal_type}, Amount: {opening_bal}")
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating supplier: {str(e)}")
        raise ValueError("Failed to update supplier.")


def delete_supplier(db: Session, supplier_id: int) -> bool:
    """Delete a supplier."""
    user = get_supplier_by_id(db, supplier_id)
    print("================",user)
    if not user:
        return False

    has_invoice = db.query(PurchaseInvoice).filter(PurchaseInvoice.supplier_id == supplier_id).first()
    if has_invoice:
        logger.warning(f"Cannot delete supplier {user.name} because they have purchases invoices")
        raise ValueError("Can't delete the supplier because they have purchase invoices")
    
    db.delete(user)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting supplier: {str(e)}")
        raise ValueError("Failed to delete supplier.")
