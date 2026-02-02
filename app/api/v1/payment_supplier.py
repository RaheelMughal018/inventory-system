"""Direct Payment Routes"""

from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.services.payment_supplier import DirectPaymentService
from app.schemas.payment_supplier import (
    DirectPaymentCreate,
    DirectPaymentResponse,
    SupplierOutstandingBalance,
    PaymentSimulation
)
from app.logger_config import logger

router = APIRouter()

@router.post(
    "/",
    response_model=DirectPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Make direct payment to supplier",
    description="""
    Pay supplier directly - payment auto-allocated across invoices.
    
    **Example Scenario:**
    - Jan 31: Purchase 2,00,000 (unpaid)
    - Feb 1: Purchase 3,00,000 (unpaid)
    - Total: 5,00,000
    - Pay: 3,50,000
    
    **Result (FIFO):**
    - First invoice: PAID (2,00,000)
    - Second invoice: PARTIAL (1,50,000 paid, 1,50,000 remaining)
    
    **Allocation Methods:**
    - FIFO: Oldest first (recommended)
    - LIFO: Newest first
    - PROPORTIONAL: Distributed proportionally
    """
)
async def create_direct_payment(
    payment_data: DirectPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Make direct payment to supplier."""
    try:
        service = DirectPaymentService(db)
        result = service.create_direct_payment(
            supplier_id=payment_data.supplier_id,
            amount=payment_data.amount,
            account_id=payment_data.account_id,
            allocation_method=payment_data.allocation_method,
            notes=payment_data.notes,
        )
        return DirectPaymentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/suppliers/{supplier_id}/outstanding",
    response_model=SupplierOutstandingBalance,
    summary="Get supplier outstanding balance",
    description="""
    Get detailed outstanding balance for a supplier.
    
    Shows:
    - Total debit (purchases)
    - Total credit (payments)
    - Outstanding balance
    - List of unpaid/partial invoices
    """
)
async def get_supplier_outstanding(
    supplier_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get supplier outstanding balance."""
    try:
        service = DirectPaymentService(db)
        result = service.get_supplier_outstanding_balance(supplier_id)
        return SupplierOutstandingBalance(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/suppliers/{supplier_id}/simulate",
    response_model=PaymentSimulation,
    summary="Simulate payment allocation",
    description="""
    Simulate how payment will be allocated WITHOUT creating it.
    
    Use this to show users the allocation before confirming payment.
    """
)
async def simulate_payment(
    supplier_id: int = Path(..., gt=0),
    amount: Decimal = Query(..., gt=0),
    allocation_method: str = Query(default="FIFO"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Simulate payment allocation."""
    try:
        service = DirectPaymentService(db)
        result = service.simulate_payment(supplier_id, amount, allocation_method)
        return PaymentSimulation(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


