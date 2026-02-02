"""Direct Payment Schemas"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DirectPaymentCreate(BaseModel):
    """Create direct payment request"""
    supplier_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    account_id: str = Field(..., min_length=1)
    allocation_method: str = Field(default="FIFO", description="FIFO, LIFO, or PROPORTIONAL")
    notes: Optional[str] = Field(default=None, max_length=500)
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v.as_tuple().exponent < -2:
            raise ValueError('Max 2 decimal places')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "amount": 350000.00,
                "account_id": "ACC-CASH1",
                "allocation_method": "FIFO",
                "notes": "Payment for Jan-Feb purchases"
            }
        }


class PaymentAllocation(BaseModel):
    """Payment allocation detail"""
    payment_id: str
    invoice_id: str
    allocated_amount: float
    invoice_status: str


class DirectPaymentResponse(BaseModel):
    """Direct payment response"""
    supplier_id: int
    supplier_name: str
    total_payment: float
    payment_account: str
    allocation_method: str
    invoices_affected: int
    allocations: List[PaymentAllocation]
    payment_date: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "supplier_name": "John Suppliers Ltd",
                "total_payment": 350000.00,
                "payment_account": "Cash",
                "allocation_method": "FIFO",
                "invoices_affected": 2,
                "allocations": [
                    {
                        "payment_id": "PAY-ABC123",
                        "invoice_id": "PINV-001",
                        "allocated_amount": 200000.00,
                        "invoice_status": "PAID"
                    },
                    {
                        "payment_id": "PAY-XYZ456",
                        "invoice_id": "PINV-002",
                        "allocated_amount": 150000.00,
                        "invoice_status": "PARTIAL"
                    }
                ],
                "payment_date": "2024-02-02T15:30:00"
            }
        }


class OutstandingInvoice(BaseModel):
    """Outstanding invoice detail"""
    invoice_id: str
    invoice_date: str
    total_amount: float
    paid_amount: float
    balance_due: float
    status: str
    days_outstanding: int


class SupplierOutstandingBalance(BaseModel):
    """Supplier outstanding balance"""
    supplier_id: int
    supplier_name: str
    supplier_user_id: str
    total_debit: float
    total_credit: float
    outstanding_balance: float
    outstanding_invoices_count: int
    outstanding_invoices: List[OutstandingInvoice]
    
    class Config:
        json_schema_extra = {
            "example": {
                "supplier_id": 1,
                "supplier_name": "John Suppliers Ltd",
                "supplier_user_id": "SUP-JOHN001",
                "total_debit": 500000.00,
                "total_credit": 0.00,
                "outstanding_balance": 500000.00,
                "outstanding_invoices_count": 2,
                "outstanding_invoices": [
                    {
                        "invoice_id": "PINV-001",
                        "invoice_date": "2024-01-31T10:00:00",
                        "total_amount": 200000.00,
                        "paid_amount": 0.00,
                        "balance_due": 200000.00,
                        "status": "UNPAID",
                        "days_outstanding": 2
                    }
                ]
            }
        }


class SimulationAllocation(BaseModel):
    """Simulated allocation"""
    invoice_id: str
    current_due: float
    will_pay: float
    remaining: float
    status: str


class PaymentSimulation(BaseModel):
    """Payment simulation result"""
    message: str
    payment_amount: float
    allocation_method: str
    invoices_affected: int
    allocations: List[SimulationAllocation]