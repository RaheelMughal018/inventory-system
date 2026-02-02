from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from starlette.status import HTTP_201_CREATED
from app.core.dependencies import get_db, get_current_active_user
from app.models.payment import PaymentAccountType
from app.models.user import User
from app.schemas.financial_ledger import FinancialLedgerResponse
from app.services.account_service import (
    create_account,
    get_account_by_id,
    get_account_by_name,
    get_all_accounts,
    update_account,
    delete_account
)
from app.schemas.account import (
    AccountDeleteResponse,
    AccountResponse,
    AccountListResponse,
    AccountCreate,
    UpdateAccount,
)
from app.logger_config import logger
from app.services.financial_ledger import FinancialLedgerService

router = APIRouter()


@router.get("", response_model=FinancialLedgerResponse)
def get_list_financial_ledger(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=20),
    search: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = FinancialLedgerService(db)

        ledgers, count, totals = service.financial_all_financial_ledger(
            skip=skip,
            limit=limit,
            search=search,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        return FinancialLedgerResponse(
            data=ledgers,
            count=count,
            total_dic=totals,
        )

    except Exception as e:
        logger.exception("Error fetching financial ledger")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch ledgers",
        )


