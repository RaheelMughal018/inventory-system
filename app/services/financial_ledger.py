from typing import List, Optional, Tuple
from sqlalchemy import Date, DateTime, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from app.logger_config import logger
from app.models.financial_ledger import FinancialLedger
from app.models.user import User


class FinancialLedgerService:
    """
    getting the financial ledger
    """
    def __init__(self, db:Session):
        self.db = db

    # ================= GET FINANCIAL LEDGER===================

    def financial_all_financial_ledger(
        self,
        skip: int = 0,
        limit: int = 25,
        search: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[FinancialLedger], int, dict]:

        try:
            query = self.db.query(FinancialLedger).options(joinedload(FinancialLedger.user))


            if user_id:
                query = query.filter(FinancialLedger.user_id == user_id)

            if search:
                query = query.filter(
                    or_(
                        FinancialLedger.ref_type.ilike(f"%{search}%"),
                        FinancialLedger.ref_id.ilike(f"%{search}%"),
                        # User.name.ilike(f"%{search}%")
                    )
                )

            # Date range filtering
            if start_date:
                query = query.filter(
                    cast(FinancialLedger.created_at, Date) >= start_date
                )
                logger.debug(f"Filtering by start_date: {start_date}")

            if end_date:
                query = query.filter(
                    cast(FinancialLedger.created_at, Date) <= end_date
                )
                logger.debug(f"Filtering by end_date: {end_date}")
            # Count (before pagination)
            total_count = query.count()

            # Totals
            totals_row = query.with_entities(
                func.coalesce(func.sum(FinancialLedger.debit), 0),
                func.coalesce(func.sum(FinancialLedger.credit), 0),
            ).first()

            totals = {
                "total_debit": float(totals_row[0]),
                "total_credit": float(totals_row[1]),
            }

            # Pagination
            rows = (
                query
                .order_by(FinancialLedger.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
                
            )

            return rows, total_count, totals

        except Exception as e:
            logger.exception("Error while fetching financial ledger")
            return [], 0, {"total_debit": 0, "total_credit": 0} 