from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import Date, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from app.logger_config import logger
from app.models.expense import Expense, ExpenseCategory
from app.models.financial_ledger import FinancialLedger
from app.models.payment import PaymentAccount


def _today() -> date:
    return date.today()


def _ledger_user_id(expense_user_id: Optional[int], ledger_user_id: Optional[int]) -> int:
    """User ID for financial ledger: expense user if set, else provided ledger user (e.g. current_user)."""
    if expense_user_id is not None:
        return expense_user_id
    if ledger_user_id is not None:
        return ledger_user_id
    raise ValueError("Ledger user_id required when expense user_id is not set (FinancialLedger.user_id is required).")


def create_expense(
    db: Session,
    amount: Decimal,
    name: str,
    account_id: str,
    expense_category_id: str,
    description: Optional[str] = None,
    user_id: Optional[int] = None,
    expense_date: Optional[date] = None,
    ledger_user_id: Optional[int] = None,
) -> Expense:
    """Create a single expense; date defaults to today. Creates a financial ledger entry (debit=amount)."""
    d = expense_date or _today()
    expense = Expense(
        date=d,
        amount=amount,
        name=name,
        account_id=account_id,
        expense_category_id=expense_category_id,
        description=description,
        user_id=user_id,
    )
    db.add(expense)
    db.flush()  # get expense.id for ledger
    ledger_user = _ledger_user_id(user_id, ledger_user_id)
    ledger_entry = FinancialLedger(
        user_id=ledger_user,
        ref_type="EXPENSE",
        ref_id=expense.id,
        debit=amount,
        credit=Decimal("0.00"),
        expense_id=expense.id,
    )
    db.add(ledger_entry)
    try:
        db.commit()
        db.refresh(expense)
        return expense
    except Exception as e:
        db.rollback()
        logger.exception("Error creating expense")
        raise ValueError("Failed to create expense.")


def create_expenses_bulk(
    db: Session,
    items: List[dict],
    expense_date: Optional[date] = None,
    ledger_user_id: Optional[int] = None,
) -> List[Expense]:
    """Create multiple expenses for a day (e.g. current day). Creates a financial ledger entry per expense. items: list of {amount, account_id, expense_category_id, description?, user_id?}."""
    d = expense_date or _today()
    created = []
    for item in items:
        expense = Expense(
            date=d,
            amount=item["amount"],
            name=item["name"],
            account_id=item["account_id"],
            expense_category_id=item["expense_category_id"],
            description=item.get("description"),
            user_id=item.get("user_id"),
        )
        db.add(expense)
        db.flush()
        ledger_user = _ledger_user_id(item.get("user_id"), ledger_user_id)
        ledger_entry = FinancialLedger(
            user_id=ledger_user,
            ref_type="EXPENSE",
            ref_id=expense.id,
            debit=expense.amount,
            credit=Decimal("0.00"),
            expense_id=expense.id,
        )
        db.add(ledger_entry)
        created.append(expense)
    try:
        db.commit()
        for exp in created:
            db.refresh(exp)
        return created
    except Exception as e:
        db.rollback()
        logger.exception("Error creating bulk expenses")
        raise ValueError("Failed to create expenses.")


def get_all_expenses(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    expense_category_id: Optional[str] = None,
    expense_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
) -> Tuple[List[Expense], int, Decimal]:
    """List expenses with filters: user, category, day (or date range), search (name, description, category). Returns (rows, total_count, total_amount)."""
    query = (
        db.query(Expense)
        .options(
            joinedload(Expense.account),
            joinedload(Expense.category),
            joinedload(Expense.user),
        )
    )
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
    if expense_category_id:
        query = query.filter(Expense.expense_category_id == expense_category_id)
    if expense_date is not None:
        query = query.filter(cast(Expense.date, Date) == expense_date)
    if start_date is not None:
        query = query.filter(cast(Expense.date, Date) >= start_date)
    if end_date is not None:
        query = query.filter(cast(Expense.date, Date) <= end_date)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.outerjoin(ExpenseCategory, Expense.expense_category_id == ExpenseCategory.id).filter(
            or_(
                Expense.name.ilike(term),
                Expense.description.ilike(term),
                ExpenseCategory.name.ilike(term),
            )
        )

    total_count = query.count()
    total_row = query.with_entities(func.coalesce(func.sum(Expense.amount), 0)).first()
    total_amount = Decimal(str(total_row[0])) if total_row else Decimal("0")

    rows = (
        query.order_by(Expense.date.desc(), Expense.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rows, total_count, total_amount


def get_total_expense_today(db: Session, user_id: Optional[int] = None) -> Tuple[date, Decimal, int]:
    """Total expense amount for today; optional filter by user. Returns (date, total_amount, count)."""
    today = _today()
    query = db.query(Expense).filter(cast(Expense.date, Date) == today)
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
    total_row = query.with_entities(
        func.coalesce(func.sum(Expense.amount), 0),
        func.count(Expense.id),
    ).first()
    total_amount = Decimal(str(total_row[0])) if total_row else Decimal("0")
    count = int(total_row[1]) if total_row else 0
    return today, total_amount, count
