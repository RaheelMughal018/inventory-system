"""
Direct Supplier Payment Service
Handles payments directly to suppliers (not tied to specific invoices)
Useful for paying down total outstanding balance

Example Scenario:
- Jan 31: Purchase ₹2,00,000 (unpaid) → Debit ₹2,00,000
- Feb 1: Purchase ₹3,00,000 (unpaid) → Debit ₹3,00,000
- Total outstanding: ₹5,00,000
- Feb 2: Pay ₹3,50,000 → Oldest invoices paid first (FIFO)
- Result: First invoice PAID (₹2,00,000), Second invoice PARTIAL (₹1,50,000)
- Remaining outstanding: ₹1,50,000
"""

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.core.dependencies import get_current_active_user
from app.models.stock import PurchaseInvoice, InvoiceStatus
from app.models.item_category import generate_custom_id
from app.models.financial_ledger import FinancialLedger
from app.models.payment import Payment, PaymentType, PaymentAccount
from app.models.user import User, UserRole
from app.logger_config import logger


class DirectPaymentService:
    """Service for handling direct payments to suppliers."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_supplier_outstanding_balance(self, supplier_id: int) -> Dict[str, Any]:
        """Get detailed outstanding balance for a supplier."""
        try:
            logger.info(f"Calculating outstanding balance for supplier {supplier_id}")
            
            # Validate supplier
            supplier = self.db.query(User).filter(
                User.id == supplier_id,
                User.role == UserRole.supplier
            ).first()
            
            if not supplier:
                raise ValueError(f"Supplier {supplier_id} not found")
            
            # Get from financial ledger
            ledger = self.db.query(
                func.sum(FinancialLedger.debit).label('total_debit'),
                func.sum(FinancialLedger.credit).label('total_credit')
            ).filter(FinancialLedger.user_id == supplier_id).first()
            
            total_debit = ledger.total_debit or Decimal('0.00')
            total_credit = ledger.total_credit or Decimal('0.00')
            outstanding = total_debit - total_credit
            
            # Get invoice details
            invoices = self.db.query(PurchaseInvoice).filter(
                PurchaseInvoice.supplier_id == supplier_id,
                PurchaseInvoice.balance_due > 0
            ).order_by(PurchaseInvoice.created_at.asc()).all()
            
            invoice_list = [{
                "invoice_id": inv.id,
                "invoice_date": inv.created_at.isoformat(),
                "total_amount": float(inv.total_amount),
                "paid_amount": float(inv.paid_amount),
                "balance_due": float(inv.balance_due),
                "status": inv.payment_status.value,
                "days_outstanding": (datetime.now() - inv.created_at).days
            } for inv in invoices]
            
            return {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name,
                "supplier_user_id": supplier.user_id,
                "total_debit": float(total_debit),
                "total_credit": float(total_credit),
                "outstanding_balance": float(outstanding),
                "outstanding_invoices_count": len(invoices),
                "outstanding_invoices": invoice_list
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error calculating balance: {str(e)}")
            raise
    
    def create_direct_payment(
        self,
        supplier_id: int,
        amount: Decimal,
        account_id: str,
        allocation_method: str = "FIFO",
        notes: Optional[str] = None,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """
        Create direct payment and allocate across invoices.
        
        Allocation methods:
        - OUTSTANDING: Pay all outstanding balance
        - EXCEEDS: Pay amount that exceeds outstanding balance reject the payment
        - FIFO: Pay oldest invoices first (default, recommended)
        - LIFO: Pay newest invoices first
        - PROPORTIONAL: Distribute proportionally
        """
        outstanding = self.get_supplier_outstanding_balance(supplier_id)

        if amount > outstanding["outstanding_balance"]:
            raise ValueError(
                f"Payment amount exceeds supplier outstanding balance "
                f"({outstanding['outstanding_balance']})"
            )

        logger.info(f"Direct payment - Supplier: {supplier_id}, Amount: {amount}")
        
        try:
            # Validate
            supplier = self.db.query(User).filter(
                User.id == supplier_id,
                User.role == UserRole.supplier
            ).first()
            if not supplier:
                raise ValueError(f"Supplier {supplier_id} not found")
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            account = self.db.query(PaymentAccount).filter(
                PaymentAccount.id == account_id
            ).first()
            if not account:
                raise ValueError(f"Payment account {account_id} not found")
            
            # Get outstanding invoices (sorted by method)
            query = self.db.query(PurchaseInvoice).filter(
                PurchaseInvoice.supplier_id == supplier_id,
                PurchaseInvoice.balance_due > 0
            )
            
            if allocation_method == "FIFO":
                invoices = query.order_by(PurchaseInvoice.created_at.asc()).all()
            elif allocation_method == "LIFO":
                invoices = query.order_by(PurchaseInvoice.created_at.desc()).all()
            else:  # PROPORTIONAL
                invoices = query.order_by(PurchaseInvoice.created_at.asc()).all()
            
            if not invoices:
                raise ValueError("No outstanding invoices found")
            
            # Allocate payment
            allocations = self._allocate_payment(amount, invoices, allocation_method)
            
            # Create payment records
            payment_records = []
            for allocation in allocations:
                invoice = allocation['invoice']
                allocated = allocation['amount']
                
                if allocated <= 0:
                    continue
                
                # Create payment
                payment_id = generate_custom_id("PAY", length=5)
                payment = Payment(
                    id=payment_id,
                    user_id=supplier_id,
                    purchase_invoice_id=invoice.id,
                    sale_invoice_id=None,
                    amount=allocated,
                    account_id=account_id,
                    payment_type=PaymentType.FULL if allocated >= invoice.balance_due else PaymentType.PARTIAL
                )
                self.db.add(payment)
                
                # Update invoice
                invoice.paid_amount += allocated
                invoice.balance_due -= allocated
                invoice.payment_status = InvoiceStatus.PAID if invoice.balance_due == 0 else InvoiceStatus.PARTIAL
                
                payment_records.append({
                    "payment_id": payment_id,
                    "invoice_id": invoice.id,
                    "allocated_amount": float(allocated),
                    "invoice_status": invoice.payment_status.value
                })
            
            # Create financial ledger entry
            ledger = FinancialLedger(
                user_id=supplier_id,
                ref_type="DIRECT_PAYMENT",
                ref_id=f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                debit=Decimal('0.00'),
                credit=amount
            )
            self.db.add(ledger)
            
            self.db.commit()
            
            logger.info(f"✅ Payment complete - {len(payment_records)} invoices affected")
            
            return {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name,
                "total_payment": float(amount),
                "payment_account": account.name,
                "allocation_method": allocation_method,
                "invoices_affected": len(payment_records),
                "allocations": payment_records,
                "payment_date": datetime.now().isoformat()
            }
            
        except ValueError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error: {str(e)}")
            raise ValueError(f"Payment failed: {str(e)}")
    
    def _allocate_payment(self, amount: Decimal, invoices: List, method: str) -> List:
        """Allocate payment across invoices."""
        allocations = []
        remaining = amount
        
        if method in ["FIFO", "LIFO"]:
            for invoice in invoices:
                if remaining <= 0:
                    break
                allocated = min(remaining, invoice.balance_due)
                allocations.append({"invoice": invoice, "amount": allocated})
                remaining -= allocated
        
        elif method == "PROPORTIONAL":
            total_due = sum(inv.balance_due for inv in invoices)
            for invoice in invoices:
                proportion = invoice.balance_due / total_due
                allocated = min(amount * proportion, invoice.balance_due)
                allocations.append({"invoice": invoice, "amount": allocated})
        
        return allocations
    
    def simulate_payment(
        self,
        supplier_id: int,
        amount: Decimal,
        allocation_method: str = "FIFO"
    ) -> Dict[str, Any]:
        """Simulate payment allocation without creating it."""
        try:
            outstanding = self.get_supplier_outstanding_balance(supplier_id)

            if amount > outstanding["outstanding_balance"]:
                return {
                    "message": f"Payment amount exceeds supplier outstanding balance "
                    f"({outstanding['outstanding_balance']}). Please reduce the payment amount.",
                    "allocations": [],
                    "payment_amount": float(amount),
                    "allocation_method": allocation_method,
                    "invoices_affected": 0,
                }

            query = self.db.query(PurchaseInvoice).filter(
                PurchaseInvoice.supplier_id == supplier_id,
                PurchaseInvoice.balance_due > 0
            )
            
            if allocation_method == "FIFO":
                invoices = query.order_by(PurchaseInvoice.created_at.asc()).all()
            else:
                invoices = query.order_by(PurchaseInvoice.created_at.desc()).all()
            
            if not invoices:
                return {"message": "No outstanding invoices", "allocations": []}
            
            allocations = self._allocate_payment(amount, invoices, allocation_method)
            
            simulation = []
            for allocation in allocations:
                invoice = allocation['invoice']
                allocated = allocation['amount']
                simulation.append({
                    "invoice_id": invoice.id,
                    "current_due": float(invoice.balance_due),
                    "will_pay": float(allocated),
                    "remaining": float(invoice.balance_due - allocated),
                    "status": "PAID" if allocated >= invoice.balance_due else "PARTIAL"
                })
            
            return {
                "message": "Payment simulation successful",
                "payment_amount": float(amount),
                "allocation_method": allocation_method,
                "invoices_affected": len(simulation),
                "allocations": simulation
            }
            
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            raise