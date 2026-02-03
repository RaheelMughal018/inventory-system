from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_active_user
from app.logger_config import logger
from app.models.user import User
from app.schemas.stock_ledger import StockLedgerResponse
from app.services.stock_ledger import StockLedgerService

router = APIRouter()


@router.get("", response_model=StockLedgerResponse)
def get_list_stock_ledger(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    item_id: Optional[str] = Query(None),
    ref_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = StockLedgerService(db)

        rows, count, totals = service.get_all_stock_ledger(
            skip=skip,
            limit=limit,
            search=search,
            item_id=item_id,
            ref_type=ref_type,
            start_date=start_date,
            end_date=end_date,
        )

        return StockLedgerResponse(
            data=rows,
            count=count,
            total_dic=totals,
        )

    except Exception as e:
        logger.exception("Error fetching stock ledger")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stock ledger",
        )
