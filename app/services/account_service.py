from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from typing import Optional, List
from decimal import Decimal
from app.models.item_category import generate_custom_id
from app.models.payment import Payment, PaymentAccountType, PaymentAccount, AccountLedger

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
        logger.error(
            f"Error fetching payment account by name {name}: {str(e)}")
        return None


def get_all_accounts(
    db: Session,
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


def get_account_balance(db: Session, account_id: str) -> Decimal:
    """
    Get current balance of a payment account.
    Current balance is updated directly on every transaction.
    """
    account = get_account_by_id(db, account_id)
    if not account:
        raise ValueError(f"Account {account_id} not found")
    return account.current_balance or Decimal("0.00")


def add_account_ledger_entry(
    db: Session,
    account_id: str,
    ref_type: str,
    ref_id: Optional[str] = None,
    debit: Decimal = Decimal("0.00"),
    credit: Decimal = Decimal("0.00"),
) -> AccountLedger:
    """Record a debit or credit to an account (e.g. PAYMENT_SUPPLIER, PAYMENT_PURCHASE, PAYMENT_SALE, EXPENSE, OPENING_BALANCE)."""
    entry = AccountLedger(
        account_id=account_id,
        ref_type=ref_type,
        ref_id=ref_id,
        debit=debit,
        credit=credit,
    )
    db.add(entry)
    return entry


def create_account(
    db: Session,
    name: str,
    type: PaymentAccountType,
    opening_balance: Optional[Decimal] = None,
) -> PaymentAccount:
    """Create a new payment account with optional opening balance. Sets current_balance = opening_balance."""

    account_id = generate_custom_id("ACC")

    while get_account_by_id(db, account_id):
        account_id = generate_custom_id("ACC")

    opening = opening_balance if opening_balance is not None else Decimal("0.00")

    account = PaymentAccount(
        id=account_id,
        name=name,
        type=type,
        opening_balance=opening,
        current_balance=opening,  # Set current balance equal to opening balance
    )

    db.add(account)
    db.flush()

    if opening > 0:
        add_account_ledger_entry(
            db,
            account_id=account_id,
            ref_type="OPENING_BALANCE",
            ref_id=f"OB-{account_id}",
            debit=Decimal("0.00"),
            credit=opening,
        )

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
    """Update payment account. If opening_balance changes, adjust current_balance accordingly."""

    account = get_account_by_id(db, account_id)
    if not account:
        return None

    if name is not None:
        account.name = name

    if type is not None:
        account.type = type

    if opening_balance is not None:
        old_opening = account.opening_balance or Decimal("0.00")
        difference = opening_balance - old_opening
        
        # Update opening balance
        account.opening_balance = opening_balance
        
        # Adjust current balance by the difference
        account.current_balance = (account.current_balance or Decimal("0.00")) + difference
        
        # Update or create ledger entry
        ob_entry = db.query(AccountLedger).filter(
            AccountLedger.account_id == account_id,
            AccountLedger.ref_type == "OPENING_BALANCE"
        ).first()
        if ob_entry:
            ob_entry.credit = opening_balance
            ob_entry.debit = Decimal("0.00")
        elif opening_balance > 0:
            add_account_ledger_entry(
                db,
                account_id=account_id,
                ref_type="OPENING_BALANCE",
                ref_id=f"OB-{account_id}",
                debit=Decimal("0.00"),
                credit=opening_balance,
            )

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
