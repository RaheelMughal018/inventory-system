# app/services/purchase_service.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime

from app.models.stock import (
    PurchaseInvoice, 
    PurchaseItem, 
    Stock, 
    InvoiceStatus
)
from app.models.item_category import Item, generate_custom_id
from app.models.financial_ledger import FinancialLedger
from app.models.payment import Payment, PaymentType, PaymentAccount
from app.models.user import User, UserRole
from app.logger_config import logger


# ==================== HELPER FUNCTIONS ====================

def get_user_balance(db: Session, user_id: int) -> Decimal:
    """
    Get current balance for a user (supplier or customer).
    Balance = Sum of all debits - Sum of all credits
    Positive = They owe you (customer) OR you owe them (supplier)
    """
    try:
        total_debit = db.query(func.sum(FinancialLedger.debit)).filter(
            FinancialLedger.user_id == user_id
        ).scalar() or Decimal("0.00")
        
        total_credit = db.query(func.sum(FinancialLedger.credit)).filter(
            FinancialLedger.user_id == user_id
        ).scalar() or Decimal("0.00")
        
        balance = total_debit - total_credit
        
        logger.debug(f"User {user_id} balance calculated: Debit={total_debit}, Credit={total_credit}, Balance={balance}")
        return balance
        
    except Exception as e:
        logger.error(f"Error calculating user balance for user_id {user_id}: {str(e)}")
        return Decimal("0.00")


def calculate_weighted_average(
    current_qty: int,
    current_avg_price: Decimal,
    new_qty: int,
    new_price: Decimal
) -> Decimal:
    """
    Calculate weighted average price.
    Formula: (old_qty * old_price + new_qty * new_price) / (old_qty + new_qty)
    """
    if current_qty + new_qty == 0:
        logger.warning("Weighted average calculation with zero total quantity")
        return Decimal("0.00")
    
    current_value = Decimal(str(current_qty)) * current_avg_price
    new_value = Decimal(str(new_qty)) * new_price
    total_qty = Decimal(str(current_qty + new_qty))
    
    weighted_avg = (current_value + new_value) / total_qty
    
    logger.debug(
        f"Weighted average calculated: "
        f"Current({current_qty} @ {current_avg_price}) + "
        f"New({new_qty} @ {new_price}) = "
        f"Total({total_qty} @ {weighted_avg})"
    )
    
    return weighted_avg


# ==================== PURCHASE INVOICE QUERIES ====================

def get_purchase_invoice_by_id(db: Session, invoice_id: str) -> Optional[PurchaseInvoice]:
    """Get purchase invoice by ID with all related data."""
    try:
        invoice = (db.query(PurchaseInvoice)
                  .options(
                      joinedload(PurchaseInvoice.supplier),
                      joinedload(PurchaseInvoice.items).joinedload(PurchaseItem.item),
                      joinedload(PurchaseInvoice.payments)
                  )
                  .filter(PurchaseInvoice.id == invoice_id)
                  .first())
        
        if invoice:
            logger.debug(f"Purchase invoice found: {invoice_id}")
        else:
            logger.warning(f"Purchase invoice not found: {invoice_id}")
            
        return invoice
        
    except Exception as e:
        logger.error(f"Error fetching purchase invoice {invoice_id}: {str(e)}")
        return None


def get_all_purchase_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    supplier_id: Optional[int] = None,
    payment_status: Optional[InvoiceStatus] = None,
    search: Optional[str] = None
) -> tuple[List[PurchaseInvoice], int]:
    """Get all purchase invoices with optional filtering."""
    try:
        query = (db.query(PurchaseInvoice)
                .options(
                    joinedload(PurchaseInvoice.supplier),
                    joinedload(PurchaseInvoice.items)
                ))
        
        # Apply filters
        if supplier_id:
            query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
            logger.debug(f"Filtering by supplier_id: {supplier_id}")
        
        if payment_status:
            query = query.filter(PurchaseInvoice.payment_status == payment_status)
            logger.debug(f"Filtering by payment_status: {payment_status}")
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(PurchaseInvoice.id.ilike(search_term))
            logger.debug(f"Searching with term: {search}")
        
        total = query.count()
        invoices = query.order_by(PurchaseInvoice.created_at.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(invoices)} purchase invoices out of {total} total")
        return invoices, total
        
    except Exception as e:
        logger.error(f"Error fetching purchase invoices: {str(e)}")
        return [], 0


# ==================== CREATE PURCHASE INVOICE ====================

def create_purchase_invoice(
    db: Session,
    supplier_id: int,
    items: List[Dict],  # [{"item_id": "ITM-XXX", "quantity": 10, "unit_price": 50.00}, ...]
    performed_by_id: int
) -> PurchaseInvoice:
    """
    Create a purchase invoice and update stock with weighted average pricing.
    
    Args:
        db: Database session
        supplier_id: ID of the supplier
        items: List of items with quantity and unit_price
        performed_by_id: ID of the user creating this invoice (owner)
    
    Returns:
        Created PurchaseInvoice object
    
    Process:
        1. Validate supplier exists
        2. Validate all items exist
        3. Calculate total amount
        4. Create purchase invoice
        5. For each item:
           - Calculate weighted average price
           - Update item stock and average price
           - Create stock ledger entry
           - Create purchase item entry
        6. Create financial ledger entry (debit - you owe supplier)
    """
    
    logger.info(f"Starting purchase invoice creation - Supplier: {supplier_id}, Items: {len(items)}, By: {performed_by_id}")
    
    try:
        # 1. Validate supplier exists and is actually a supplier
        supplier = db.query(User).filter(
            User.id == supplier_id,
            User.role == UserRole.supplier
        ).first()
        
        if not supplier:
            logger.error(f"Supplier validation failed: ID {supplier_id} not found or not a supplier")
            raise ValueError("Supplier not found or invalid supplier role")
        
        logger.info(f"Supplier validated: {supplier.name} ({supplier.user_id})")
        
        # 2. Validate all items exist and calculate total
        total_amount = Decimal("0.00")
        validated_items = []
        
        for idx, item_data in enumerate(items):
            item_id = item_data.get("item_id")
            quantity = int(item_data.get("quantity", 0))
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            
            logger.debug(f"Processing item {idx + 1}: ID={item_id}, Qty={quantity}, Price={unit_price}")
            
            # Validation
            if quantity <= 0:
                logger.error(f"Invalid quantity for item {item_id}: {quantity}")
                raise ValueError(f"Quantity must be greater than 0 for item {item_id}")
            
            if unit_price <= 0:
                logger.error(f"Invalid price for item {item_id}: {unit_price}")
                raise ValueError(f"Unit price must be greater than 0 for item {item_id}")
            
            # Check if item exists
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.error(f"Item not found: {item_id}")
                raise ValueError(f"Item {item_id} not found")
            
            item_total = quantity * unit_price
            total_amount += item_total
            
            validated_items.append({
                "item": item,
                "item_id": item_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "total": item_total
            })
            
            logger.debug(f"Item validated: {item.name} - Qty: {quantity}, Price: {unit_price}, Total: {item_total}")
        
        if not validated_items:
            logger.error("No items provided for purchase invoice")
            raise ValueError("No items provided for purchase invoice")
        
        logger.info(f"All items validated. Total items: {len(validated_items)}, Total amount: {total_amount}")
        
        # 3. Create purchase invoice
        invoice_id = generate_custom_id("PINV", length=8)
        
        # Ensure invoice_id is unique
        attempts = 0
        while get_purchase_invoice_by_id(db, invoice_id):
            invoice_id = generate_custom_id("PINV", length=8)
            attempts += 1
            if attempts > 10:
                logger.error("Failed to generate unique invoice ID after 10 attempts")
                raise ValueError("Failed to generate unique invoice ID")
        
        invoice = PurchaseInvoice(
            id=invoice_id,
            supplier_id=supplier_id,
            total_amount=total_amount,
            paid_amount=Decimal("0.00"),
            balance_due=total_amount,
            payment_status=InvoiceStatus.UNPAID
        )
        
        db.add(invoice)
        db.flush()  # Flush to get invoice ID for relationships
        
        logger.info(f"Purchase invoice created: {invoice_id} - Total: {total_amount}")
        
        # 4. Process each item: update stock, create ledger entries
        for item_data in validated_items:
            item = item_data["item"]
            quantity = item_data["quantity"]
            unit_price = item_data["unit_price"]
            
            # Store values before update
            qty_before = item.total_quantity
            avg_price_before = item.avg_price
            
            logger.debug(
                f"Before update - Item: {item.id}, "
                f"Qty: {qty_before}, Avg Price: {avg_price_before}"
            )
            
            # Calculate new weighted average price
            new_avg_price = calculate_weighted_average(
                current_qty=qty_before,
                current_avg_price=avg_price_before,
                new_qty=quantity,
                new_price=unit_price
            )
            
            # Update item
            item.total_quantity += quantity
            item.avg_price = new_avg_price
            
            logger.info(
                f"Stock updated - Item: {item.name} ({item.id}), "
                f"Qty: {qty_before} → {item.total_quantity}, "
                f"Avg Price: {avg_price_before} → {new_avg_price}"
            )
            
            # Create stock ledger entry
            stock_id = generate_custom_id("STK", length=8)
            stock_entry = Stock(
                id=stock_id,
                item_id=item.id,
                ref_type="PURCHASE",
                ref_id=invoice.id,
                qty_in=quantity,
                qty_out=0,
                unit_price=unit_price
            )
            db.add(stock_entry)
            
            logger.debug(f"Stock ledger entry created: {stock_id}")
            
            # Create purchase item
            purchase_item = PurchaseItem(
                invoice_id=invoice.id,
                item_id=item.id,
                quantity=quantity,
                unit_price=unit_price
            )
            db.add(purchase_item)
            
            logger.debug(f"Purchase item entry created for invoice {invoice.id}")
        
        # 5. Create financial ledger entry (you owe supplier)
        supplier_balance_before = get_user_balance(db, supplier_id)
        
        ledger_entry = FinancialLedger(
            user_id=supplier_id,
            ref_type="PURCHASE",
            ref_id=invoice.id,
            debit=total_amount,  # You owe the supplier
            credit=Decimal("0.00")
        )
        db.add(ledger_entry)
        
        supplier_balance_after = supplier_balance_before + total_amount
        
        logger.info(
            f"Financial ledger entry created - Supplier: {supplier.name}, "
            f"Debit: {total_amount}, "
            f"Balance: {supplier_balance_before} → {supplier_balance_after}"
        )
        
        # Commit transaction
        db.commit()
        db.refresh(invoice)
        
        logger.info(
            f"✅ Purchase invoice completed successfully: {invoice.id} - "
            f"Supplier: {supplier.name} ({supplier.user_id}) - "
            f"Amount: {total_amount} - "
            f"Items: {len(validated_items)} - "
            f"Created by: {performed_by_id}"
        )
        
        return invoice
        
    except ValueError as ve:
        db.rollback()
        logger.error(f"Validation error in purchase invoice creation: {str(ve)}")
        raise
        
    except IntegrityError as ie:
        db.rollback()
        logger.error(f"Database integrity error in purchase invoice creation: {str(ie)}")
        raise ValueError("Failed to create purchase invoice due to database constraint.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in purchase invoice creation: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to create purchase invoice: {str(e)}")


# ==================== PAYMENT OPERATIONS ====================

def create_purchase_payment(
    db: Session,
    invoice_id: str,
    amount: Decimal,
    account_id: str,
    performed_by_id: int
) -> Payment:
    """
    Record a payment for a purchase invoice.
    
    Process:
        1. Validate invoice exists
        2. Validate payment amount doesn't exceed balance due
        3. Create payment record
        4. Update invoice paid_amount and balance_due
        5. Update invoice payment_status
        6. Create financial ledger entry (credit - you paid supplier)
    """
    
    logger.info(
        f"Starting payment creation - Invoice: {invoice_id}, "
        f"Amount: {amount}, Account: {account_id}, By: {performed_by_id}"
    )
    
    try:
        # 1. Validate invoice
        invoice = get_purchase_invoice_by_id(db, invoice_id)
        if not invoice:
            logger.error(f"Invoice not found: {invoice_id}")
            raise ValueError("Purchase invoice not found")
        
        logger.info(
            f"Invoice found: {invoice_id} - "
            f"Total: {invoice.total_amount}, "
            f"Paid: {invoice.paid_amount}, "
            f"Due: {invoice.balance_due}"
        )
        
        # 2. Validate amount
        if amount <= 0:
            logger.error(f"Invalid payment amount: {amount}")
            raise ValueError("Payment amount must be greater than 0")
        
        if amount > invoice.balance_due:
            logger.error(
                f"Payment amount ({amount}) exceeds balance due ({invoice.balance_due})"
            )
            raise ValueError(
                f"Payment amount ({amount}) exceeds balance due ({invoice.balance_due})"
            )
        
        # 3. Validate payment account
        account = db.query(PaymentAccount).filter(PaymentAccount.id == account_id).first()
        if not account:
            logger.error(f"Payment account not found: {account_id}")
            raise ValueError("Payment account not found")
        
        logger.info(f"Payment account validated: {account.name} ({account.type})")
        
        # 4. Create payment
        payment_id = generate_custom_id("PAY", length=8)
        
        # Determine payment type
        payment_type = PaymentType.FULL if amount >= invoice.balance_due else PaymentType.PARTIAL
        
        payment = Payment(
            id=payment_id,
            user_id=invoice.supplier_id,
            purchase_invoice_id=invoice.id,
            sale_invoice_id=None,
            amount=amount,
            account_id=account_id,
            payment_type=payment_type
        )
        db.add(payment)
        
        logger.debug(f"Payment record created: {payment_id} - Type: {payment_type}")
        
        # 5. Update invoice
        old_paid = invoice.paid_amount
        old_due = invoice.balance_due
        old_status = invoice.payment_status
        
        invoice.paid_amount += amount
        invoice.balance_due -= amount
        
        # Update payment status
        if invoice.balance_due == 0:
            invoice.payment_status = InvoiceStatus.PAID
        elif invoice.paid_amount > 0:
            invoice.payment_status = InvoiceStatus.PARTIAL
        
        logger.info(
            f"Invoice updated: {invoice.id} - "
            f"Paid: {old_paid} → {invoice.paid_amount}, "
            f"Due: {old_due} → {invoice.balance_due}, "
            f"Status: {old_status} → {invoice.payment_status}"
        )
        
        # 6. Create financial ledger entry (credit - you paid supplier)
        supplier_balance_before = get_user_balance(db, invoice.supplier_id)
        
        ledger_entry = FinancialLedger(
            user_id=invoice.supplier_id,
            ref_type="PAYMENT",
            ref_id=payment.id,
            debit=Decimal("0.00"),
            credit=amount  # You paid the supplier
        )
        db.add(ledger_entry)
        
        supplier_balance_after = supplier_balance_before - amount
        
        logger.info(
            f"Financial ledger entry created - "
            f"Credit: {amount}, "
            f"Balance: {supplier_balance_before} → {supplier_balance_after}"
        )
        
        # Commit transaction
        db.commit()
        db.refresh(payment)
        
        logger.info(
            f"✅ Payment completed successfully: {payment.id} - "
            f"Invoice: {invoice.id} - "
            f"Amount: {amount} - "
            f"Account: {account.name} - "
            f"Remaining balance: {invoice.balance_due}"
        )
        
        return payment
        
    except ValueError as ve:
        db.rollback()
        logger.error(f"Validation error in payment creation: {str(ve)}")
        raise
        
    except IntegrityError as ie:
        db.rollback()
        logger.error(f"Database integrity error in payment creation: {str(ie)}")
        raise ValueError("Failed to create payment due to database constraint.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in payment creation: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to create payment: {str(e)}")


def get_purchase_invoice_payments(db: Session, invoice_id: str) -> List[Payment]:
    """Get all payments for a purchase invoice."""
    try:
        payments = (db.query(Payment)
                   .options(joinedload(Payment.account))
                   .filter(Payment.purchase_invoice_id == invoice_id)
                   .order_by(Payment.created_at.desc())
                   .all())
        
        logger.info(f"Retrieved {len(payments)} payments for invoice {invoice_id}")
        return payments
        
    except Exception as e:
        logger.error(f"Error fetching payments for invoice {invoice_id}: {str(e)}")
        return []


def delete_payment(db: Session, payment_id: str) -> bool:
    """
    Delete a payment and reverse the financial entries.
    This will increase the invoice balance_due again.
    """
    logger.info(f"Starting payment deletion: {payment_id}")
    
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.warning(f"Payment not found: {payment_id}")
            return False
        
        # Get invoice
        invoice = None
        if payment.purchase_invoice_id:
            invoice = get_purchase_invoice_by_id(db, payment.purchase_invoice_id)
        
        if not invoice:
            logger.error(f"Invoice not found for payment: {payment_id}")
            raise ValueError("Associated invoice not found")
        
        amount = payment.amount
        
        logger.info(
            f"Deleting payment: {payment_id} - "
            f"Amount: {amount} - "
            f"Invoice: {invoice.id}"
        )
        
        # Update invoice
        invoice.paid_amount -= amount
        invoice.balance_due += amount
        
        # Update payment status
        if invoice.paid_amount == 0:
            invoice.payment_status = InvoiceStatus.UNPAID
        elif invoice.balance_due > 0:
            invoice.payment_status = InvoiceStatus.PARTIAL
        
        # Delete financial ledger entry
        ledger_entry = db.query(FinancialLedger).filter(
            FinancialLedger.ref_type == "PAYMENT",
            FinancialLedger.ref_id == payment_id
        ).first()
        
        if ledger_entry:
            db.delete(ledger_entry)
            logger.debug(f"Financial ledger entry deleted for payment {payment_id}")
        
        # Delete payment
        db.delete(payment)
        db.commit()
        
        logger.info(
            f"✅ Payment deleted successfully: {payment_id} - "
            f"Invoice {invoice.id} balance restored: {invoice.balance_due}"
        )
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting payment {payment_id}: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to delete payment: {str(e)}")


# ==================== SUPPLIER BALANCE QUERIES ====================

def get_supplier_outstanding_balance(db: Session, supplier_id: int) -> Decimal:
    """
    Get total outstanding balance for a supplier.
    This is the amount you owe them.
    """
    try:
        balance = get_user_balance(db, supplier_id)
        logger.info(f"Supplier {supplier_id} outstanding balance: {balance}")
        return balance
        
    except Exception as e:
        logger.error(f"Error getting supplier balance for {supplier_id}: {str(e)}")
        return Decimal("0.00")


def get_supplier_purchase_summary(db: Session, supplier_id: int) -> Dict:
    """Get purchase summary for a supplier."""
    try:
        logger.info(f"Generating purchase summary for supplier: {supplier_id}")
        
        # Get supplier info
        supplier = db.query(User).filter(User.id == supplier_id).first()
        if not supplier:
            logger.warning(f"Supplier not found: {supplier_id}")
            raise ValueError("Supplier not found")
        
        # Total purchases
        total_purchases = db.query(func.sum(PurchaseInvoice.total_amount)).filter(
            PurchaseInvoice.supplier_id == supplier_id
        ).scalar() or Decimal("0.00")
        
        # Total paid
        total_paid = db.query(func.sum(PurchaseInvoice.paid_amount)).filter(
            PurchaseInvoice.supplier_id == supplier_id
        ).scalar() or Decimal("0.00")
        
        # Outstanding balance
        outstanding = get_supplier_outstanding_balance(db, supplier_id)
        
        # Count of invoices by status
        total_invoices = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.supplier_id == supplier_id
        ).count()
        
        unpaid_count = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.supplier_id == supplier_id,
            PurchaseInvoice.payment_status == InvoiceStatus.UNPAID
        ).count()
        
        partial_count = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.supplier_id == supplier_id,
            PurchaseInvoice.payment_status == InvoiceStatus.PARTIAL
        ).count()
        
        paid_count = db.query(PurchaseInvoice).filter(
            PurchaseInvoice.supplier_id == supplier_id,
            PurchaseInvoice.payment_status == InvoiceStatus.PAID
        ).count()
        
        summary = {
            "supplier_id": supplier_id,
            "supplier_name": supplier.name,
            "supplier_user_id": supplier.user_id,
            "total_purchases": float(total_purchases),
            "total_paid": float(total_paid),
            "outstanding_balance": float(outstanding),
            "total_invoices": total_invoices,
            "unpaid_invoices": unpaid_count,
            "partial_invoices": partial_count,
            "paid_invoices": paid_count
        }
        
        logger.info(
            f"Purchase summary generated for {supplier.name}: "
            f"Purchases={total_purchases}, Paid={total_paid}, Outstanding={outstanding}"
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating supplier summary for {supplier_id}: {str(e)}")
        raise


# ==================== STOCK QUERIES ====================

def get_item_stock_history(
    db: Session,
    item_id: str,
    limit: int = 50
) -> List[Stock]:
    """Get stock movement history for an item."""
    try:
        stock_entries = (db.query(Stock)
                        .filter(Stock.item_id == item_id)
                        .order_by(Stock.created_at.desc())
                        .limit(limit)
                        .all())
        
        logger.info(f"Retrieved {len(stock_entries)} stock entries for item {item_id}")
        return stock_entries
        
    except Exception as e:
        logger.error(f"Error fetching stock history for item {item_id}: {str(e)}")
        return []


def get_all_stock_movements(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    ref_type: Optional[str] = None
) -> tuple[List[Stock], int]:
    """Get all stock movements with optional filtering."""
    try:
        query = db.query(Stock).options(joinedload(Stock.item))
        
        if ref_type:
            query = query.filter(Stock.ref_type == ref_type)
            logger.debug(f"Filtering stock movements by ref_type: {ref_type}")
        
        total = query.count()
        stock_entries = query.order_by(Stock.created_at.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(stock_entries)} stock movements out of {total} total")
        return stock_entries, total
        
    except Exception as e:
        logger.error(f"Error fetching stock movements: {str(e)}")
        return [], 0