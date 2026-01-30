"""
Purchase Module Routes - Unified Version
FastAPI router providing REST API endpoints for all purchase operations
Aligned with unified_purchase_service.py and unified_purchase_schemas.py
"""

from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import (
    # Request schemas
    PurchaseInvoiceCreate,
    PaymentCreate,
    PurchaseInvoiceFilters,
    StockLedgerFilters,
    
    # Response schemas
    PurchaseInvoiceResponse,
    PurchaseInvoiceSummary,
    PurchaseInvoiceListResponse,
    PaymentResponse,
    ItemStockSummary,
    SupplierBalance,
    SupplierPurchaseSummary,
    StockLedgerEntry,
    StockLedgerListResponse,
    SuccessResponse,
    ErrorResponse,
    
    # Enums
    InvoiceStatusEnum
)
from app.logger_config import logger


router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def build_purchase_invoice_response(invoice) -> PurchaseInvoiceResponse:
    """Build a complete invoice response with all relationships."""
    items = []
    for item in invoice.items:
        items.append({
            "id": item.id,
            "item_id": item.item_id,
            "item_name": item.item.name if item.item else "Unknown",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": item.quantity * item.unit_price
        })
    
    payments = []
    for payment in invoice.payments:
        payments.append({
            "id": payment.id,
            "amount": payment.amount,
            "account_id": payment.account_id,
            "account_name": payment.account.name if payment.account else None,
            "account_type": payment.account.type.value if payment.account else None,
            "payment_type": payment.payment_type.value,
            "created_at": payment.created_at
        })
    
    return PurchaseInvoiceResponse(
        id=invoice.id,
        supplier_id=invoice.supplier_id,
        supplier={
            "id": invoice.supplier.id,
            "user_id": invoice.supplier.user_id,
            "name": invoice.supplier.name,
            "email": invoice.supplier.email
        },
        total_amount=invoice.total_amount,
        paid_amount=invoice.paid_amount,
        balance_due=invoice.balance_due,
        payment_status=invoice.payment_status.value,
        created_at=invoice.created_at,
        items=items,
        payments=payments
    )


def build_invoice_summary(invoice) -> PurchaseInvoiceSummary:
    """Build invoice summary for list views."""
    return PurchaseInvoiceSummary(
        id=invoice.id,
        supplier_id=invoice.supplier_id,
        supplier_name=invoice.supplier.name,
        supplier_user_id=invoice.supplier.user_id,
        total_amount=invoice.total_amount,
        paid_amount=invoice.paid_amount,
        balance_due=invoice.balance_due,
        payment_status=invoice.payment_status.value,
        created_at=invoice.created_at,
        item_count=len(invoice.items),
        payment_count=len(invoice.payments)
    )


# ============================================================================
# Purchase Invoice Endpoints
# ============================================================================

@router.post(
    "/",
    response_model=PurchaseInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new purchase invoice",
    description="""
    Create a new purchase invoice with items, stock entries, and optional payment.
    
    This endpoint handles the complete purchase workflow:
    1. Validates supplier and items
    2. Creates purchase invoice
    3. Records purchased items
    4. Updates stock ledger with qty_in
    5. Calculates and updates item weighted average prices
    6. Creates financial ledger entries (debit - you owe supplier)
    7. Processes payment if provided (credit - you pay supplier)
    
    **Important Notes:**
    - All items must exist in the system
    - Quantities and prices must be positive
    - If payment_amount > 0, payment_account_id is required
    - Average price is calculated as: (old_value + new_value) / (old_qty + new_qty)
    """,
    responses={
        201: {"description": "Purchase invoice created successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Supplier or item not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
def create_purchase_invoice(
    purchase_data: PurchaseInvoiceCreate,
    db: Session = Depends(get_db),
    # In production, get this from authenticated user
    performed_by_id: Optional[int] = Query(default=1, description="ID of user creating this purchase")
):
    """
    Create a new purchase invoice.
    
    **Example Request:**
    ```json
    {
        "supplier_id": 1,
        "items": [
            {"item_id": "ITM-ABC123", "quantity": 10, "unit_price": 2.00},
            {"item_id": "ITM-XYZ789", "quantity": 5, "unit_price": 3.50}
        ],
        "payment_amount": 20.00,
        "payment_account_id": "ACC-CASH1",
    }
    ```
    """
    try:
        logger.info(f"API: Creating purchase invoice for supplier {purchase_data.supplier_id}")
        
        service = PurchaseService(db)
        
        # Convert Pydantic model to dict for service
        items = [item.model_dump() for item in purchase_data.items]
        
        invoice = service.create_purchase(
            supplier_id=purchase_data.supplier_id,
            items=items,
            payment_amount=purchase_data.payment_amount or Decimal('0.00'),
            payment_account_id=purchase_data.payment_account_id,
            performed_by_id=performed_by_id
        )
        
        logger.info(f"API: Purchase invoice created successfully: {invoice.id}")
        
        # Build and return response
        return build_purchase_invoice_response(invoice)
        
    except ValueError as e:
        logger.error(f"API: Validation error in purchase creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API: Unexpected error in purchase creation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create purchase invoice: {str(e)}"
        )


@router.get(
    "/",
    response_model=PurchaseInvoiceListResponse,
    summary="List all purchase invoices",
    description="""
    Get a paginated list of purchase invoices with optional filtering.
    
    **Filters:**
    - `supplier_id`: Filter by specific supplier
    - `payment_status`: Filter by payment status (PAID, PARTIAL, UNPAID)
    - `search`: Search in invoice IDs
    - `skip`: Pagination offset
    - `limit`: Number of records to return (max 500)
    """
)
async def list_purchase_invoices(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of records to return"),
    supplier_id: Optional[int] = Query(default=None, description="Filter by supplier ID"),
    payment_status: Optional[InvoiceStatusEnum] = Query(default=None, description="Filter by payment status"),
    search: Optional[str] = Query(default=None, max_length=100, description="Search in invoice IDs"),
    db: Session = Depends(get_db)
):
    """Get a list of purchase invoices with filtering and pagination."""
    try:
        logger.info(f"API: Listing purchase invoices - skip={skip}, limit={limit}, supplier_id={supplier_id}")
        
        service = PurchaseService(db)
        
        invoices, total = service.get_all_purchase_invoices(
            skip=skip,
            limit=limit,
            supplier_id=supplier_id,
            payment_status=payment_status,
            search=search
        )
        
        # Build summary responses
        summaries = [build_invoice_summary(inv) for inv in invoices]
        
        logger.info(f"API: Retrieved {len(summaries)} invoices out of {total} total")
        
        return PurchaseInvoiceListResponse(
            invoices=summaries,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"API: Error listing purchase invoices: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve purchase invoices: {str(e)}"
        )


@router.get(
    "/invoices/{invoice_id}",
    response_model=PurchaseInvoiceResponse,
    summary="Get purchase invoice details",
    description="Get detailed information about a specific purchase invoice including all items and payments.",
    responses={
        200: {"description": "Purchase invoice retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Purchase invoice not found"}
    }
)
def get_purchase_invoice(
    invoice_id: str = Path(..., description="Purchase invoice ID"),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific purchase invoice."""
    try:
        logger.info(f"API: Retrieving purchase invoice: {invoice_id}")
        
        service = PurchaseService(db)
        invoice = service.get_purchase_invoice(invoice_id)
        
        if not invoice:
            logger.warning(f"API: Purchase invoice not found: {invoice_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase invoice {invoice_id} not found"
            )
        
        logger.info(f"API: Purchase invoice retrieved: {invoice_id}")
        return build_purchase_invoice_response(invoice)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error retrieving purchase invoice {invoice_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve purchase invoice: {str(e)}"
        )


# ============================================================================
# Payment Endpoints
# ============================================================================

@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add payment to purchase invoice",
    description="""
    Add a payment to an existing purchase invoice.
    
    This will:
    1. Validate payment amount doesn't exceed balance due
    2. Create payment record
    3. Update invoice paid_amount and balance_due
    4. Update payment_status (PAID/PARTIAL/UNPAID)
    5. Create financial ledger entry (credit - you paid supplier)
    
    **Note:** Payment amount cannot exceed the invoice's balance due.
    """,
    responses={
        201: {"description": "Payment added successfully"},
        400: {"model": ErrorResponse, "description": "Validation error (amount exceeds balance)"},
        404: {"model": ErrorResponse, "description": "Invoice or payment account not found"}
    }
)
def add_payment_to_invoice(
    invoice_id: str = Path(..., description="Purchase invoice ID"),
    payment_data: PaymentCreate = ...,
    db: Session = Depends(get_db),
    performed_by_id: Optional[int] = Query(default=1, description="ID of user making payment")
):
    """
    Add a payment to an existing purchase invoice.
    
    **Example Request:**
    ```json
    {
        "amount": 15.50,
        "account_id": "ACC-BANK1",
        "notes": "Partial payment via bank transfer"
    }
    ```
    """
    try:
        logger.info(f"API: Adding payment to invoice {invoice_id}, amount: {payment_data.amount}")
        
        service = PurchaseService(db)
        
        payment = service.add_payment_to_purchase(
            invoice_id=invoice_id,
            amount=payment_data.amount,
            account_id=payment_data.account_id,
            performed_by_id=performed_by_id
        )
        
        logger.info(f"API: Payment added successfully: {payment.id}")
        
        return PaymentResponse(
            id=payment.id,
            amount=payment.amount,
            account_id=payment.account_id,
            account_name=payment.account.name if payment.account else None,
            account_type=payment.account.type.value if payment.account else None,
            payment_type=payment.payment_type.value,
            created_at=payment.created_at
        )
        
    except ValueError as e:
        logger.error(f"API: Validation error adding payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API: Unexpected error adding payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment: {str(e)}"
        )


@router.get(
    "/invoices/{invoice_id}/payments",
    response_model=List[PaymentResponse],
    summary="Get all payments for an invoice",
    description="Get all payments made for a specific purchase invoice."
)
def get_invoice_payments(
    invoice_id: str = Path(..., description="Purchase invoice ID"),
    db: Session = Depends(get_db)
):
    """Get all payments for a specific purchase invoice."""
    try:
        logger.info(f"API: Retrieving payments for invoice: {invoice_id}")
        
        service = PurchaseService(db)
        
        # First check if invoice exists
        invoice = service.get_purchase_invoice(invoice_id)
        if not invoice:
            logger.warning(f"API: Invoice not found: {invoice_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase invoice {invoice_id} not found"
            )
        
        payments = service.get_purchase_invoice_payments(invoice_id)
        
        # Build response
        payment_responses = []
        for payment in payments:
            payment_responses.append(PaymentResponse(
                id=payment.id,
                amount=payment.amount,
                account_id=payment.account_id,
                account_name=payment.account.name if payment.account else None,
                account_type=payment.account.type.value if payment.account else None,
                payment_type=payment.payment_type.value,
                created_at=payment.created_at
            ))
        
        logger.info(f"API: Retrieved {len(payment_responses)} payments for invoice {invoice_id}")
        return payment_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error retrieving payments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(e)}"
        )


@router.delete(
    "/payments/{payment_id}",
    response_model=SuccessResponse,
    summary="Delete a payment",
    description="""
    Delete a payment and reverse the financial entries.
    
    This will:
    1. Delete the payment record
    2. Increase invoice balance_due
    3. Decrease invoice paid_amount
    4. Update payment_status
    5. Delete financial ledger entry
    
    **Warning:** This action cannot be undone.
    """,
    responses={
        200: {"description": "Payment deleted successfully"},
        404: {"model": ErrorResponse, "description": "Payment not found"}
    }
)
def delete_payment(
    payment_id: str = Path(..., description="Payment ID to delete"),
    db: Session = Depends(get_db)
):
    """Delete a payment and reverse the financial entries."""
    try:
        logger.info(f"API: Deleting payment: {payment_id}")
        
        service = PurchaseService(db)
        success = service.delete_payment(payment_id)
        
        if not success:
            logger.warning(f"API: Payment not found: {payment_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment {payment_id} not found"
            )
        
        logger.info(f"API: Payment deleted successfully: {payment_id}")
        return SuccessResponse(
            message="Payment deleted successfully",
            data={"payment_id": payment_id}
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"API: Error deleting payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API: Unexpected error deleting payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete payment: {str(e)}"
        )


# ============================================================================
# Supplier Endpoints
# ============================================================================

@router.get(
    "/suppliers/{supplier_id}/invoices",
    response_model=PurchaseInvoiceListResponse,
    summary="Get all purchases from a supplier",
    description="Get all purchase invoices from a specific supplier with optional status filter."
)
def get_supplier_invoices(
    supplier_id: int = Path(..., gt=0, description="Supplier ID"),
    payment_status: Optional[InvoiceStatusEnum] = Query(default=None, description="Filter by payment status"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all purchase invoices from a specific supplier."""
    try:
        logger.info(f"API: Retrieving invoices for supplier {supplier_id}")
        
        service = PurchaseService(db)
        
        invoices, total = service.get_all_purchase_invoices(
            skip=skip,
            limit=limit,
            supplier_id=supplier_id,
            payment_status=payment_status
        )
        
        summaries = [build_invoice_summary(inv) for inv in invoices]
        
        logger.info(f"API: Retrieved {len(summaries)} invoices for supplier {supplier_id}")
        
        return PurchaseInvoiceListResponse(
            invoices=summaries,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"API: Error retrieving supplier invoices: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve supplier invoices: {str(e)}"
        )


@router.get(
    "/suppliers/{supplier_id}/balance",
    response_model=SupplierBalance,
    summary="Get supplier balance",
    description="""
    Get the current balance with a supplier from the financial ledger.
    
    **Balance Calculation:**
    - total_debit: Sum of all debits (purchases - you owe them)
    - total_credit: Sum of all credits (payments - you paid them)
    - balance: Debit - Credit (positive = you owe them, negative = they owe you)
    """
)
def get_supplier_balance(
    supplier_id: int = Path(..., gt=0, description="Supplier ID"),
    db: Session = Depends(get_db)
):
    """Get the current balance with a supplier."""
    try:
        logger.info(f"API: Retrieving balance for supplier {supplier_id}")
        
        service = PurchaseService(db)
        balance_data = service.get_supplier_balance(supplier_id)
        
        # Get supplier info
        from app.models.user import User
        supplier = db.query(User).filter(User.id == supplier_id).first()
        
        logger.info(f"API: Balance retrieved for supplier {supplier_id}: {balance_data['balance']}")
        
        return SupplierBalance(
            supplier_id=supplier_id,
            supplier_name=supplier.name if supplier else None,
            supplier_user_id=supplier.user_id if supplier else None,
            total_debit=balance_data['total_debit'],
            total_credit=balance_data['total_credit'],
            balance=balance_data['balance']
        )
        
    except Exception as e:
        logger.error(f"API: Error retrieving supplier balance: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supplier balance: {str(e)}"
        )


@router.get(
    "/suppliers/summary",
    response_model=List[SupplierPurchaseSummary],
    summary="Get supplier purchase summary",
    description="""
    Get comprehensive purchase summary for a supplier.
    
    Includes:
    - Total purchase amount
    - Total paid amount
    - Outstanding balance
    - Invoice counts by status (unpaid, partial, paid)
    """
)
def get_all_suppliers_summary(
    db: Session = Depends(get_db)
):
    """Get comprehensive purchase summary for a supplier."""
    try:
        logger.info(f"API: Generating summary for suppliers")
        
        service = PurchaseService(db)
        summaries = service.get_all_suppliers_purchase_summary()
        
        logger.info(f"API: Summary generated for suppliers")
        
        return summaries
        
    except ValueError as e:
        logger.error(f"API: Error generating suppliers summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API: Unexpected error generating summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suppliers summary: {str(e)}"
        )


# ============================================================================
# Stock & Inventory Endpoints
# ============================================================================

@router.get(
    "/items/{item_id}/stock",
    response_model=ItemStockSummary,
    summary="Get item stock summary",
    description="""
    Get comprehensive stock summary for an item.
    
    Returns:
    - Current quantity in stock
    - Weighted average price
    - Total value (quantity × avg_price)
    - Total quantity in (all purchases)
    - Total quantity out (all sales)
    - Unit type (PCS, SET, etc.)
    """
)
def get_item_stock(
    item_id: str = Path(..., description="Item ID"),
    db: Session = Depends(get_db)
):
    """Get comprehensive stock summary for an item."""
    try:
        logger.info(f"API: Retrieving stock summary for item {item_id}")
        
        service = PurchaseService(db)
        stock_data = service.get_item_stock_summary(item_id)
        
        logger.info(f"API: Stock summary retrieved for item {item_id}")
        
        return ItemStockSummary(**stock_data)
        
    except ValueError as e:
        logger.error(f"API: Item not found: {item_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API: Error retrieving stock summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stock summary: {str(e)}"
        )


@router.get(
    "/items/{item_id}/history",
    response_model=List[StockLedgerEntry],
    summary="Get item stock history",
    description="Get stock movement history for an item (purchases, sales, adjustments)."
)
def get_item_history(
    item_id: str = Path(..., description="Item ID"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get stock movement history for an item."""
    try:
        logger.info(f"API: Retrieving stock history for item {item_id}")
        
        service = PurchaseService(db)
        stock_entries = service.get_item_stock_history(item_id, limit=limit)
        
        # Build response
        entries = []
        for entry in stock_entries:
            entries.append(StockLedgerEntry(
                id=entry.id,
                item_id=entry.item_id,
                item_name=entry.item.name if entry.item else None,
                ref_type=entry.ref_type,
                ref_id=entry.ref_id,
                qty_in=entry.qty_in,
                qty_out=entry.qty_out,
                unit_price=entry.unit_price,
                created_at=entry.created_at
            ))
        
        logger.info(f"API: Retrieved {len(entries)} stock history entries for item {item_id}")
        return entries
        
    except Exception as e:
        logger.error(f"API: Error retrieving stock history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stock history: {str(e)}"
        )


@router.get(
    "/stock-ledger",
    response_model=StockLedgerListResponse,
    summary="Get stock ledger entries",
    description="""
    Get stock ledger entries with optional filters.
    
    Use this to track all stock movements across items.
    
    **Filters:**
    - `item_id`: Filter by specific item
    - `ref_type`: Filter by reference type (PURCHASE, SALE, ADJUSTMENT)
    """
)
def get_stock_ledger(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of records to return"),
    item_id: Optional[str] = Query(default=None, description="Filter by item ID"),
    ref_type: Optional[str] = Query(default=None, description="Filter by reference type"),
    db: Session = Depends(get_db)
):
    """Get stock ledger entries with optional filters."""
    try:
        logger.info(f"API: Retrieving stock ledger - item_id={item_id}, ref_type={ref_type}")
        
        service = PurchaseService(db)
        stock_entries, total = service.get_all_stock_movements(
            skip=skip,
            limit=limit,
            ref_type=ref_type
        )
        # If item_id filter is provided, filter further
        if item_id:
            stock_entries = [e for e in stock_entries if e.item_id == item_id]
            total = len(stock_entries)
        
        # Build response
        entries = []
        for entry in stock_entries:
            entries.append(StockLedgerEntry(
                id=entry.id,
                item_id=entry.item_id,
                item_name=entry.item.name if entry.item else None,
                ref_type=entry.ref_type,
                ref_id=entry.ref_id,
                qty_in=entry.qty_in,
                qty_out=entry.qty_out,
                unit_price=entry.unit_price,
                created_at=entry.created_at
            ))
        
        logger.info(f"API: Retrieved {len(entries)} stock ledger entries")
        
        return StockLedgerListResponse(
            entries=entries,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"API: Error retrieving stock ledger: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stock ledger: {str(e)}"
        )


