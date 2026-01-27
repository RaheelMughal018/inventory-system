"""
Purchase Module Schemas - Unified Version
Pydantic schemas for request validation and response serialization
Aligned with unified_purchase_service.py
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class InvoiceStatusEnum(str, Enum):
    """Invoice payment status"""
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"


class PaymentTypeEnum(str, Enum):
    """Payment type"""
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    UN_PAID = "UN_PAID"


class PaymentAccountTypeEnum(str, Enum):
    """Payment account types"""
    CASH = "CASH"
    BANK = "BANK"
    JAZZCASH = "JAZZCASH"
    EASYPAISA = "EASYPAISA"


# ============================================================================
# Request Schemas - Purchase Invoice
# ============================================================================

class PurchaseItemCreate(BaseModel):
    """Schema for creating a purchase item"""
    item_id: str = Field(..., description="Item ID to purchase", min_length=1)
    quantity: int = Field(..., gt=0, description="Quantity to purchase (must be positive)")
    unit_price: Decimal = Field(..., gt=0, description="Unit price (must be positive)")
    
    @field_validator('unit_price')
    @classmethod
    def validate_unit_price(cls, v):
        """Ensure unit price has at most 2 decimal places"""
        if v.as_tuple().exponent < -2:
            raise ValueError('Unit price must have at most 2 decimal places')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "ITM-ABC123",
                "quantity": 10,
                "unit_price": 2.50
            }
        }


class PurchaseInvoiceCreate(BaseModel):
    """Schema for creating a new purchase invoice"""
    supplier_id: int = Field(..., gt=0, description="Supplier user ID")
    items: List[PurchaseItemCreate] = Field(
        ..., 
        min_length=1, 
        description="List of items to purchase (at least one required)"
    )
    payment_amount: Optional[Decimal] = Field(
        default=Decimal('0.00'), 
        ge=0, 
        description="Amount paid during purchase"
    )
    payment_account_id: Optional[str] = Field(
        default=None, 
        description="Payment account ID if payment is made"
    )
    
    
    @model_validator(mode='after')
    def validate_payment_account(self):
        """If payment_amount > 0, payment_account_id is required"""
        if self.payment_amount and self.payment_amount > 0:
            if not self.payment_account_id:
                raise ValueError("payment_account_id is required when payment_amount > 0")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "items": [
                    {"item_id": "ITM-ABC123", "quantity": 10, "unit_price": 2.00},
                    {"item_id": "ITM-XYZ789", "quantity": 5, "unit_price": 3.50}
                ],
                "payment_amount": 20.00,
                "payment_account_id": "ACC-CASH1",
            }
        }


# ============================================================================
# Request Schemas - Payment
# ============================================================================

class PaymentCreate(BaseModel):
    """Schema for adding payment to an invoice"""
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be positive)")
    account_id: str = Field(..., min_length=1, description="Payment account ID")
    
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Ensure amount has at most 2 decimal places"""
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount must have at most 2 decimal places')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 15.50,
                "account_id": "ACC-BANK1",
            }
        }


# ============================================================================
# Response Schemas - Purchase Item
# ============================================================================

class PurchaseItemResponse(BaseModel):
    """Schema for purchase item in response"""
    id: int
    item_id: str
    item_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "item_id": "ITM-ABC123",
                "item_name": "Widget A",
                "quantity": 10,
                "unit_price": 2.50,
                "line_total": 25.00
            }
        }


# ============================================================================
# Response Schemas - Payment
# ============================================================================

class PaymentAccountResponse(BaseModel):
    """Schema for payment account"""
    id: str
    name: str
    type: PaymentAccountTypeEnum
    
    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    """Schema for payment in response"""
    id: str
    amount: Decimal
    account_id: str
    account_name: Optional[str] = None
    account_type: Optional[PaymentAccountTypeEnum] = None
    payment_type: PaymentTypeEnum
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "PAY-ABC12345",
                "amount": 15.50,
                "account_id": "ACC-CASH1",
                "account_name": "Cash Account",
                "account_type": "CASH",
                "payment_type": "PARTIAL",
                "created_at": "2026-01-28T10:30:00"
            }
        }


# ============================================================================
# Response Schemas - Supplier
# ============================================================================

class SupplierResponse(BaseModel):
    """Schema for supplier information"""
    id: int
    user_id: str
    name: str
    email: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Response Schemas - Purchase Invoice
# ============================================================================

class PurchaseInvoiceResponse(BaseModel):
    """Schema for complete purchase invoice response"""
    id: str
    supplier_id: int
    supplier: SupplierResponse
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    payment_status: InvoiceStatusEnum
    created_at: datetime
    items: List[PurchaseItemResponse]
    payments: List[PaymentResponse]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "PINV-ABC12345",
                "supplier_id": 1,
                "supplier": {
                    "id": 1,
                    "user_id": "SUP-TEST001",
                    "name": "ABC Suppliers Ltd",
                    "email": "supplier@example.com"
                },
                "total_amount": 37.50,
                "paid_amount": 20.00,
                "balance_due": 17.50,
                "payment_status": "PARTIAL",
                "created_at": "2026-01-28T10:30:00",
                "items": [
                    {
                        "id": 1,
                        "item_id": "ITM-ABC123",
                        "item_name": "Widget A",
                        "quantity": 10,
                        "unit_price": 2.00,
                        "line_total": 20.00
                    }
                ],
                "payments": [
                    {
                        "id": "PAY-XYZ98765",
                        "amount": 20.00,
                        "account_id": "ACC-CASH1",
                        "account_name": "Cash Account",
                        "account_type": "CASH",
                        "payment_type": "PARTIAL",
                        "created_at": "2026-01-28T10:30:00"
                    }
                ]
            }
        }


class PurchaseInvoiceSummary(BaseModel):
    """Schema for purchase invoice summary (list view)"""
    id: str
    supplier_id: int
    supplier_name: str
    supplier_user_id: str
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    payment_status: InvoiceStatusEnum
    created_at: datetime
    item_count: int
    payment_count: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "PINV-ABC12345",
                "supplier_id": 1,
                "supplier_name": "ABC Suppliers Ltd",
                "supplier_user_id": "SUP-TEST001",
                "total_amount": 37.50,
                "paid_amount": 20.00,
                "balance_due": 17.50,
                "payment_status": "PARTIAL",
                "created_at": "2026-01-28T10:30:00",
                "item_count": 2,
                "payment_count": 1
            }
        }


class PurchaseInvoiceListResponse(BaseModel):
    """Schema for paginated purchase invoice list"""
    invoices: List[PurchaseInvoiceSummary]
    total: int
    skip: int
    limit: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoices": [],
                "total": 25,
                "skip": 0,
                "limit": 50
            }
        }


# ============================================================================
# Response Schemas - Stock & Ledger
# ============================================================================

class StockLedgerEntry(BaseModel):
    """Schema for stock ledger entry"""
    id: str
    item_id: str
    item_name: Optional[str] = None
    ref_type: str
    ref_id: str
    qty_in: int
    qty_out: int
    unit_price: Optional[Decimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "STK-ABC12345",
                "item_id": "ITM-ABC123",
                "item_name": "Widget A",
                "ref_type": "PURCHASE",
                "ref_id": "PINV-XYZ98765",
                "qty_in": 10,
                "qty_out": 0,
                "unit_price": 2.50,
                "created_at": "2026-01-28T10:30:00"
            }
        }


class StockLedgerListResponse(BaseModel):
    """Schema for paginated stock ledger list"""
    entries: List[StockLedgerEntry]
    total: int
    skip: int
    limit: int


class ItemStockSummary(BaseModel):
    """Schema for item stock summary"""
    item_id: str
    item_name: str
    current_quantity: int
    avg_price: Decimal
    total_value: Decimal
    total_qty_in: int
    total_qty_out: int
    unit_type: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "ITM-ABC123",
                "item_name": "Widget A",
                "current_quantity": 100,
                "avg_price": 2.50,
                "total_value": 250.00,
                "total_qty_in": 150,
                "total_qty_out": 50,
                "unit_type": "PCS"
            }
        }


# ============================================================================
# Response Schemas - Supplier Balance & Summary
# ============================================================================

class SupplierBalance(BaseModel):
    """Schema for supplier balance"""
    supplier_id: int
    supplier_name: Optional[str] = None
    supplier_user_id: Optional[str] = None
    total_debit: Decimal
    total_credit: Decimal
    balance: Decimal
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "supplier_name": "ABC Suppliers Ltd",
                "supplier_user_id": "SUP-TEST001",
                "total_debit": 150.00,
                "total_credit": 100.00,
                "balance": 50.00
            }
        }


class SupplierPurchaseSummary(BaseModel):
    """Schema for comprehensive supplier purchase summary"""
    supplier_id: int
    supplier_name: str
    supplier_user_id: str
    total_purchases: float
    total_paid: float
    outstanding_balance: float
    total_invoices: int
    unpaid_invoices: int
    partial_invoices: int
    paid_invoices: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "supplier_name": "ABC Suppliers Ltd",
                "supplier_user_id": "SUP-TEST001",
                "total_purchases": 5000.00,
                "total_paid": 3500.00,
                "outstanding_balance": 1500.00,
                "total_invoices": 10,
                "unpaid_invoices": 2,
                "partial_invoices": 3,
                "paid_invoices": 5
            }
        }


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class PurchaseInvoiceFilters(BaseModel):
    """Schema for filtering purchase invoices"""
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=500, description="Number of records to return")
    supplier_id: Optional[int] = Field(default=None, description="Filter by supplier ID")
    payment_status: Optional[InvoiceStatusEnum] = Field(
        default=None, 
        description="Filter by payment status"
    )
    search: Optional[str] = Field(
        default=None, 
        max_length=100,
        description="Search in invoice IDs"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "skip": 0,
                "limit": 50,
                "supplier_id": 1,
                "payment_status": "PARTIAL",
                "search": "PINV-2024"
            }
        }


class StockLedgerFilters(BaseModel):
    """Schema for filtering stock ledger"""
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of records to return")
    item_id: Optional[str] = Field(default=None, description="Filter by item ID")
    ref_type: Optional[str] = Field(
        default=None, 
        description="Filter by reference type (PURCHASE/SALE/ADJUSTMENT)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "skip": 0,
                "limit": 100,
                "item_id": "ITM-ABC123",
                "ref_type": "PURCHASE"
            }
        }


# ============================================================================
# Analytics & Statistics Schemas
# ============================================================================

class PurchaseAnalytics(BaseModel):
    """Schema for purchase analytics"""
    total_purchases: int
    total_amount: Decimal
    total_paid: Decimal
    total_due: Decimal
    unique_suppliers: int
    unique_items: int
    period: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_purchases": 25,
                "total_amount": 5000.00,
                "total_paid": 3500.00,
                "total_due": 1500.00,
                "unique_suppliers": 5,
                "unique_items": 15,
                "period": "January 2026"
            }
        }


class TopSupplier(BaseModel):
    """Schema for top supplier by volume"""
    supplier_id: int
    supplier_name: str
    supplier_user_id: str
    purchase_count: int
    total_amount: Decimal
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "supplier_name": "ABC Suppliers Ltd",
                "supplier_user_id": "SUP-TEST001",
                "purchase_count": 10,
                "total_amount": 2000.00
            }
        }


class TopItem(BaseModel):
    """Schema for top purchased item"""
    item_id: str
    item_name: str
    total_quantity: int
    total_value: Decimal
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "ITM-ABC123",
                "item_name": "Widget A",
                "total_quantity": 500,
                "total_value": 1250.00
            }
        }


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorDetail(BaseModel):
    """Schema for error details"""
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    errors: Optional[List[ErrorDetail]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Validation error in purchase creation",
                "errors": [
                    {
                        "field": "items.0.quantity",
                        "message": "Quantity must be greater than 0"
                    }
                ]
            }
        }


# ============================================================================
# Success Response Schemas
# ============================================================================

class SuccessResponse(BaseModel):
    """Schema for success responses"""
    message: str
    data: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Payment deleted successfully",
                "data": {"invoice_id": "PINV-ABC12345"}
            }
        }