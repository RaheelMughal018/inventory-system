from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from typing import Optional, List
from decimal import Decimal
from app.models.item_category import generate_custom_id
from app.models.payment import Payment, PaymentAccountType, PaymentAccount

from app.logger_config import logger

# ==================== QUERY OPERATIONS ====================

def get_account_by_id(db: Session, account_id: str) -> Optional[PaymentAccount]:
    """Get payment account by ID."""
    try:
        return db.query(PaymentAccount).filter(PaymentAccount.id == account_id).first()
    except Exception as e:
        logger.error(f"Error fetching payment account {account_id}: {str(e)}")
        return None


def get_account_by_name(db: Session, name: str) -> Optional[PaymentAccount]:
    """Get payment account by name."""
    try:
        return db.query(PaymentAccount).filter(PaymentAccount.name == name).first()
    except Exception as e:
        logger.error(f"Error fetching payment account by name {name}: {str(e)}")
        return None


def get_all_accounts(
    db:Session, 
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    type: Optional[PaymentAccountType] = None
    ) -> tuple[List[PaymentAccount], int]:
    """ Get all Accounts with optional filteration """
    query = db.query(PaymentAccount)

    if type:
        query = query.filter(PaymentAccount.type == type)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                PaymentAccount.name.ilike(search_term),
                PaymentAccount.id.ilike(search_term)
            )
        ) 
    
    count = query.count()
    accounts = query.offset(skip).limit(limit).all()
    return accounts, count

def create_account(
    db: Session,
    name: str,
    type: PaymentAccountType,
) -> PaymentAccount:
    """Create a new payment account."""

    if get_account_by_name(db, name):
        raise ValueError("Payment account with this name already exists")

    account_id = generate_custom_id("ACC")

    while get_account_by_id(db, account_id):
        account_id = generate_custom_id("ACC")

    account = PaymentAccount(
        id=account_id,
        name=name,
        type=type,
    )

    db.add(account)

    try:
        db.commit()
        db.refresh(account)
        return account
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating payment account: {str(e)}")
        raise ValueError("Failed to create payment account")


def update_account(
    db: Session,
    account_id: str,
    name: Optional[str] = None,
    type: Optional[PaymentAccountType] = None,
    opening_balance: Optional[Decimal] = None
) -> Optional[PaymentAccount]:
    """Update payment account."""

    account = get_account_by_id(db, account_id)
    if not account:
        return None

    if name is not None:
        account.name = name

    if type is not None:
        account.type = type

    if opening_balance is not None:
        account.opening_balance = opening_balance

    try:
        db.commit()
        db.refresh(account)
        return account
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating payment account: {str(e)}")
        raise ValueError("Failed to update payment account")


def delete_account(db: Session, account_id: str) -> bool:
    """Delete payment account."""

    account = get_account_by_id(db, account_id)
    if not account:
        return False

    # Prevent deletion if payments exist
    payments_count = (
        db.query(func.count(Payment.id))
        .filter(Payment.account_id == account_id)
        .scalar()
    )

    if payments_count > 0:
        raise ValueError("Cannot delete account with existing payments")

    db.delete(account)

    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting payment account: {str(e)}")
        raise ValueError("Failed to delete payment account")