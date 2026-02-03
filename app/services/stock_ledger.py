from typing import List, Optional, Tuple
from sqlalchemy import Date, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from app.logger_config import logger
from app.models.stock import Stock


class StockLedgerService:
    """
    Service for querying the stock ledger (stock movements by item).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all_stock_ledger(
        self,
        skip: int = 0,
        limit: int = 25,
        search: Optional[str] = None,
        item_id: Optional[str] = None,
        ref_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[Stock], int, dict]:
        try:
            query = self.db.query(Stock).options(joinedload(Stock.item))

            if item_id:
                query = query.filter(Stock.item_id == item_id)

            if ref_type:
                query = query.filter(Stock.ref_type == ref_type)

            if search:
                query = query.filter(
                    or_(
                        Stock.ref_type.ilike(f"%{search}%"),
                        Stock.ref_id.ilike(f"%{search}%"),
                        Stock.item_id.ilike(f"%{search}%"),
                    )
                )

            if start_date:
                query = query.filter(
                    cast(Stock.created_at, Date) >= start_date
                )
                logger.debug(f"Filtering by start_date: {start_date}")

            if end_date:
                query = query.filter(
                    cast(Stock.created_at, Date) <= end_date
                )
                logger.debug(f"Filtering by end_date: {end_date}")

            total_count = query.count()

            totals_row = query.with_entities(
                func.coalesce(func.sum(Stock.qty_in), 0),
                func.coalesce(func.sum(Stock.qty_out), 0),
            ).first()

            totals = {
                "total_qty_in": int(totals_row[0]),
                "total_qty_out": int(totals_row[1]),
            }

            rows = (
                query
                .order_by(Stock.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            return rows, total_count, totals

        except Exception as e:
            logger.exception("Error while fetching stock ledger")
            return [], 0, {"total_qty_in": 0, "total_qty_out": 0}
