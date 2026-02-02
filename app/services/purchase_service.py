"""
Purchase Service Layer - Unified Version
Combines best practices from both implementations:
- Class-based structure with helper functions
- Comprehensive logging from your version
- Modular design and validation from my version
- All purchase operations including invoice creation, payments, and queries
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any
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


def get_user_balance(db: Session, user_id: int) -> Decimal:
    """
    Get current balance for a user (supplier or customer).
    Balance = Sum of all debits - Sum of all credits
    Positive = You owe them (for suppliers)
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


def generate_unique_id(db: Session, prefix: str, model_class, length: int = 8) -> str:
    """Generate a unique ID for a model."""
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        new_id = generate_custom_id(prefix, length=length)
        existing = db.query(model_class).filter(model_class.id == new_id).first()
        
        if not existing:
            logger.debug(f"Generated unique ID: {new_id}")
            return new_id
        
        attempts += 1
    
    logger.error(f"Failed to generate unique {prefix} ID after {max_attempts} attempts")
    raise ValueError(f"Failed to generate unique {prefix} ID")


# ==================== PURCHASE SERVICE CLASS ====================

class PurchaseService:
    """
    Service class for handling all purchase-related operations.
    Implements ledger-based inventory management with weighted average price calculation.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== PURCHASE INVOICE CREATION ====================

    def create_purchase(
        self,
        supplier_id: int,
        items: List[Dict[str, Any]],
        payment_amount: Decimal = Decimal('0.00'),
        payment_account_id: Optional[str] = None,
        performed_by_id: Optional[int] = None
    ) -> PurchaseInvoice:
        """
        Create a complete purchase transaction with all ledger entries.
        
        Args:
            supplier_id: ID of the supplier
            items: List of dicts with keys: item_id, quantity, unit_price
                   Example: [{"item_id": "ITM-ABC", "quantity": 10, "unit_price": 2.50}]
            payment_amount: Amount paid at the time of purchase
            payment_account_id: Account used for payment (if any)
            performed_by_id: ID of user creating this purchase
            
        Returns:
            PurchaseInvoice: Created purchase invoice with all relationships
            
        Raises:
            ValueError: If supplier not found, items invalid, or insufficient data
            
        Process:
            1. Validate supplier exists and has correct role
            2. Validate all items exist and calculate total amount
            3. Create purchase invoice
            4. For each item:
               - Calculate weighted average price
               - Update item stock and average price
               - Create stock ledger entry (qty_in)
               - Create purchase item entry
            5. Create financial ledger entry (debit - you owe supplier)
            6. Process payment if provided
        """
        logger.info(f"Starting purchase invoice creation - Supplier: {supplier_id}, Items: {len(items)}, By: {performed_by_id}")
        
        try:
            # 1. Validate supplier
            supplier = self._validate_supplier(supplier_id)
            logger.info(f"Supplier validated: {supplier.name} ({supplier.user_id})")
            
            # 2. Validate items and calculate total
            validated_items, total_amount = self._validate_and_calculate_items(items)
            logger.info(f"All items validated. Total items: {len(validated_items)}, Total amount: {total_amount}")
            
            # 3. Calculate balance due and payment status
            balance_due = total_amount - payment_amount
            payment_status = self._determine_payment_status(total_amount, payment_amount)
            
            # 4. Create Purchase Invoice with unique ID
            invoice_id = generate_unique_id(self.db, "PINV", PurchaseInvoice, length=8)
            
            invoice = PurchaseInvoice(
                id=invoice_id,
                supplier_id=supplier_id,
                total_amount=total_amount,
                paid_amount=payment_amount,
                balance_due=balance_due,
                payment_status=payment_status
            )
            self.db.add(invoice)
            self.db.flush()  # Flush to get invoice ID for relationships
            
            logger.info(f"Purchase invoice created: {invoice_id} - Total: {total_amount}")
            
            # 5. Process each item: update stock, create ledger entries
            for item_data in validated_items:
                self._create_purchase_item_and_update_stock(invoice, item_data)
            
            # 6. Create Financial Ledger Entry for the purchase (debit - you owe supplier)
            self._create_purchase_ledger_entry(supplier_id, invoice.id, total_amount)
            
            # 7. Process payment if provided
            if payment_amount > 0 and payment_account_id:
                self._process_purchase_payment(
                    invoice,
                    supplier_id,
                    payment_amount,
                    payment_account_id
                )
            
            # Commit transaction
            self.db.commit()
            self.db.refresh(invoice)
            
            logger.info(
                f"✅ Purchase invoice completed successfully: {invoice.id} - "
                f"Supplier: {supplier.name} ({supplier.user_id}) - "
                f"Amount: {total_amount} - "
                f"Items: {len(validated_items)} - "
                f"Created by: {performed_by_id}"
            )
            
            return invoice
            
        except ValueError as ve:
            self.db.rollback()
            logger.error(f"Validation error in purchase invoice creation: {str(ve)}")
            raise
            
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Database integrity error in purchase invoice creation: {str(ie)}")
            raise ValueError("Failed to create purchase invoice due to database constraint.")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in purchase invoice creation: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to create purchase invoice: {str(e)}")

    # ==================== UPDATE INVOICE ====================

    def update_purchase_invoice(
        self,
        invoice_id: str,
        items: Optional[List[Dict[str, Any]]] = None,
        performed_by_id: Optional[int] = None
    ) -> PurchaseInvoice:
        """
        Update an existing purchase invoice.
        
        This will:
        1. Validate invoice exists and can be updated (cannot update fully paid invoices)
        2. Reverse all existing stock and ledger entries
        3. Delete existing purchase items
        4. Create new purchase items with new data
        5. Update stock with new quantities and recalculate average prices
        6. Update financial ledger entries
        7. Preserve existing payments
        
        Args:
            invoice_id: ID of the invoice to update
            items: New list of items (if None, keeps existing items)
            performed_by_id: ID of user performing the update
            
        Returns:
            Updated PurchaseInvoice
            
        Raises:
            ValueError: If invoice not found, fully paid, or has issues
        """
        logger.info(f"Starting invoice update - Invoice: {invoice_id}, By: {performed_by_id}")
        
        try:
            # 1. Get existing invoice
            invoice = self.get_purchase_invoice(invoice_id)
            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                raise ValueError(f"Purchase invoice {invoice_id} not found")
            
            # 2. Validate invoice can be updated
            # Note: We allow updating UNPAID and PARTIAL invoices
            # For PAID invoices, user should delete payments first
            if invoice.payment_status == InvoiceStatus.PAID:
                logger.error(f"Cannot update fully paid invoice: {invoice_id}")
                raise ValueError(
                    "Cannot update fully paid invoice. "
                    "Please delete payments first if you need to modify this invoice."
                )
            
            logger.info(
                f"Invoice validated for update: {invoice_id} - "
                f"Current status: {invoice.payment_status}, "
                f"Paid amount: {invoice.paid_amount}"
            )
            
            # 3. If no items provided, nothing to update
            if items is None:
                logger.warning(f"No items provided for update: {invoice_id}")
                return invoice
            
            # 4. Validate new items
            validated_items, new_total_amount = self._validate_and_calculate_items(items)
            logger.info(f"New items validated. Total items: {len(validated_items)}, New total: {new_total_amount}")
            
            # 5. Check if new total is less than already paid amount
            if new_total_amount < invoice.paid_amount:
                logger.error(
                    f"New total ({new_total_amount}) is less than paid amount ({invoice.paid_amount})"
                )
                raise ValueError(
                    f"New total amount ({new_total_amount}) cannot be less than "
                    f"already paid amount ({invoice.paid_amount}). "
                    "Please delete some payments first."
                )
            
            # 6. Reverse existing items (stock and purchase items)
            logger.info(f"Reversing existing items for invoice {invoice_id}")
            self._reverse_invoice_items(invoice)
            
            # 7. Update financial ledger for the difference
            old_total = invoice.total_amount
            difference = new_total_amount - old_total
            
            if difference != 0:
                logger.info(f"Updating financial ledger - Difference: {difference}")
                self._update_purchase_ledger(invoice.supplier_id, invoice_id, difference)
            
            # 8. Create new purchase items and update stock
            logger.info(f"Creating new items for invoice {invoice_id}")
            for item_data in validated_items:
                self._create_purchase_item_and_update_stock(invoice, item_data)
            
            # 9. Update invoice totals
            invoice.total_amount = new_total_amount
            invoice.balance_due = new_total_amount - invoice.paid_amount
            
            # 10. Update payment status
            invoice.payment_status = self._determine_payment_status(
                invoice.total_amount,
                invoice.paid_amount
            )
            
            # Commit transaction
            self.db.commit()
            self.db.refresh(invoice)
            
            logger.info(
                f"✅ Invoice updated successfully: {invoice_id} - "
                f"Old total: {old_total} → New total: {new_total_amount} - "
                f"Status: {invoice.payment_status} - "
                f"Updated by: {performed_by_id}"
            )
            
            return invoice
            
        except ValueError as ve:
            self.db.rollback()
            logger.error(f"Validation error in invoice update: {str(ve)}")
            raise
            
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Database integrity error in invoice update: {str(ie)}")
            raise ValueError("Failed to update invoice due to database constraint.")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in invoice update: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to update invoice: {str(e)}")

    def _reverse_invoice_items(self, invoice: PurchaseInvoice):
        """
        Reverse all items in an invoice by:
        1. Reversing stock quantities and recalculating average prices
        2. Deleting stock ledger entries
        3. Deleting purchase item entries
        """
        logger.info(f"Reversing items for invoice {invoice.id}")
        
        for purchase_item in invoice.items:
            item = purchase_item.item
            quantity = purchase_item.quantity
            unit_price = purchase_item.unit_price
            
            # Store values before reversal
            qty_before = item.total_quantity
            avg_price_before = item.avg_price
            
            logger.debug(
                f"Reversing item: {item.id} - "
                f"Qty: {quantity}, Price: {unit_price}"
            )
            
            # Calculate new average price after removing this purchase
            # We need to reverse the weighted average calculation
            if qty_before == quantity:
                # This was the only purchase, reset to 0
                new_avg_price = Decimal('0.00')
                new_quantity = 0
            elif qty_before > quantity:
                # Remove this purchase from the average
                # Formula: new_avg = (total_value - removed_value) / (total_qty - removed_qty)
                total_value = avg_price_before * qty_before
                removed_value = unit_price * quantity
                new_total_value = total_value - removed_value
                new_quantity = qty_before - quantity
                
                if new_quantity > 0:
                    new_avg_price = new_total_value / new_quantity
                else:
                    new_avg_price = Decimal('0.00')
                    new_quantity = 0
            else:
                # This shouldn't happen (trying to remove more than we have)
                logger.warning(
                    f"Attempting to remove {quantity} items but only {qty_before} exist for {item.id}"
                )
                new_avg_price = avg_price_before
                new_quantity = max(0, qty_before - quantity)
            
            # Update item
            item.total_quantity = new_quantity
            item.avg_price = new_avg_price
            self.db.add(item)
            
            logger.info(
                f"Stock reversed - Item: {item.name} ({item.id}), "
                f"Qty: {qty_before} → {new_quantity}, "
                f"Avg Price: {avg_price_before} → {new_avg_price}"
            )
            
            # Delete stock ledger entry for this item in this invoice
            stock_entries = self.db.query(Stock).filter(
                Stock.item_id == item.id,
                Stock.ref_type == "PURCHASE",
                Stock.ref_id == invoice.id
            ).all()
            
            for stock_entry in stock_entries:
                self.db.delete(stock_entry)
                logger.debug(f"Stock ledger entry deleted: {stock_entry.id}")
            
            # Delete purchase item
            self.db.delete(purchase_item)
            logger.debug(f"Purchase item deleted: {purchase_item.id}")

    def _update_purchase_ledger(
        self,
        supplier_id: int,
        invoice_id: str,
        difference: Decimal
    ):
        """
        Update financial ledger when invoice total changes.
        
        If difference is positive: Additional debit (you owe more)
        If difference is negative: Additional credit (you owe less)
        """
        if difference == 0:
            return
        
        supplier_balance_before = get_user_balance(self.db, supplier_id)
        
        if difference > 0:
            # Invoice total increased - you owe more
            ledger_entry = FinancialLedger(
                user_id=supplier_id,
                ref_type="PURCHASE_UPDATE",
                ref_id=invoice_id,
                debit=difference,
                credit=Decimal('0.00')
            )
            supplier_balance_after = supplier_balance_before + difference
        else:
            # Invoice total decreased - you owe less
            ledger_entry = FinancialLedger(
                user_id=supplier_id,
                ref_type="PURCHASE_UPDATE",
                ref_id=invoice_id,
                debit=Decimal('0.00'),
                credit=abs(difference)
            )
            supplier_balance_after = supplier_balance_before + difference  # difference is negative
        
        self.db.add(ledger_entry)
        
        logger.info(
            f"Financial ledger updated - Supplier ID: {supplier_id}, "
            f"Difference: {difference}, "
            f"Balance: {supplier_balance_before} → {supplier_balance_after}"
        )

    # ==================== DELETE INVOICE ====================

    def delete_purchase_invoice(
        self,
        invoice_id: str,
        performed_by_id: Optional[int] = None
    ) -> bool:
        """
        Delete a purchase invoice and reverse all related entries.
        
        This will:
        1. Validate invoice exists and can be deleted
        2. Delete all payments (if any) and reverse their ledger entries
        3. Reverse all stock entries (reduce quantities, recalculate avg prices)
        4. Delete all stock ledger entries
        5. Delete all purchase items
        6. Delete financial ledger entries for the purchase
        7. Delete the invoice itself
        
        Args:
            invoice_id: ID of the invoice to delete
            performed_by_id: ID of user performing the deletion
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If invoice not found or cannot be deleted
            
        Note:
            This is a destructive operation and cannot be undone.
            Use with caution!
        """
        logger.info(f"Starting invoice deletion - Invoice: {invoice_id}, By: {performed_by_id}")
        
        try:
            # 1. Get invoice
            invoice = self.get_purchase_invoice(invoice_id)
            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                raise ValueError(f"Purchase invoice {invoice_id} not found")
            
            logger.info(
                f"Invoice found for deletion: {invoice_id} - "
                f"Supplier: {invoice.supplier.name} - "
                f"Total: {invoice.total_amount} - "
                f"Status: {invoice.payment_status}"
            )
            
            # 2. Delete all payments first
            if invoice.payments:
                logger.info(f"Deleting {len(invoice.payments)} payments for invoice {invoice_id}")
                
                # Get payment IDs before deletion
                payment_ids = [p.id for p in invoice.payments]
                
                for payment_id in payment_ids:
                    # This will also delete financial ledger entries
                    self.delete_payment(payment_id)
                    logger.debug(f"Payment deleted during invoice deletion: {payment_id}")
            
            # 3. Reverse all items (stock and purchase items)
            logger.info(f"Reversing all items for invoice {invoice_id}")
            self._reverse_invoice_items(invoice)
            
            # 4. Delete financial ledger entries for this purchase
            ledger_entries = self.db.query(FinancialLedger).filter(
                or_(
                    FinancialLedger.ref_id == invoice_id,
                    FinancialLedger.ref_id.like(f"%{invoice_id}%")  # Also catch UPDATE entries
                )
            ).all()
            
            for ledger_entry in ledger_entries:
                self.db.delete(ledger_entry)
                logger.debug(
                    f"Financial ledger entry deleted: "
                    f"Type={ledger_entry.ref_type}, ID={ledger_entry.ref_id}"
                )
            
            # 5. Delete the invoice
            supplier_name = invoice.supplier.name
            supplier_id = invoice.supplier_id
            total_amount = invoice.total_amount
            
            self.db.delete(invoice)
            self.db.commit()
            
            logger.info(
                f"✅ Invoice deleted successfully: {invoice_id} - "
                f"Supplier: {supplier_name} (ID: {supplier_id}) - "
                f"Amount: {total_amount} - "
                f"Deleted by: {performed_by_id}"
            )
            
            return True
            
        except ValueError as ve:
            self.db.rollback()
            logger.error(f"Validation error in invoice deletion: {str(ve)}")
            raise
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in invoice deletion: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to delete invoice: {str(e)}")
    def _validate_supplier(self, supplier_id: int) -> User:
        """Validate that supplier exists and has correct role."""
        supplier = self.db.query(User).filter(
            User.id == supplier_id,
            User.role == UserRole.supplier
        ).first()
        
        if not supplier:
            logger.error(f"Supplier validation failed: ID {supplier_id} not found or not a supplier")
            raise ValueError("Supplier not found or invalid supplier role")
        
        return supplier

    def _validate_and_calculate_items(
        self, 
        items: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Decimal]:
        """
        Validate items and calculate total amount.
        
        Returns:
            Tuple of (validated_items, total_amount)
        """
        if not items or len(items) == 0:
            logger.error("No items provided for purchase invoice")
            raise ValueError("At least one item is required for purchase")
        
        validated_items = []
        total_amount = Decimal('0.00')
        
        for idx, item_data in enumerate(items):
            # Validate required fields
            if not all(k in item_data for k in ['item_id', 'quantity', 'unit_price']):
                raise ValueError("Each item must have item_id, quantity, and unit_price")
            
            item_id = item_data['item_id']
            quantity = int(item_data['quantity'])
            unit_price = Decimal(str(item_data['unit_price']))
            
            logger.debug(f"Processing item {idx + 1}: ID={item_id}, Qty={quantity}, Price={unit_price}")
            
            # Validate quantity and price
            if quantity <= 0:
                logger.error(f"Invalid quantity for item {item_id}: {quantity}")
                raise ValueError(f"Quantity must be greater than 0 for item {item_id}")
            
            if unit_price <= 0:
                logger.error(f"Invalid price for item {item_id}: {unit_price}")
                raise ValueError(f"Unit price must be greater than 0 for item {item_id}")
            
            # Validate item exists
            item = self.db.query(Item).filter(Item.id == item_id).first()
            if not item:
                logger.error(f"Item not found: {item_id}")
                raise ValueError(f"Item {item_id} not found")
            
            # Calculate line total
            line_total = unit_price * quantity
            total_amount += line_total
            
            validated_items.append({
                'item_id': item_id,
                'item': item,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': line_total
            })
            
            logger.debug(f"Item validated: {item.name} - Qty: {quantity}, Price: {unit_price}, Total: {line_total}")
        
        return validated_items, total_amount

    def _determine_payment_status(
        self, 
        total_amount: Decimal, 
        paid_amount: Decimal
    ) -> InvoiceStatus:
        """Determine the payment status based on amounts."""
        if paid_amount >= total_amount:
            return InvoiceStatus.PAID
        elif paid_amount > 0:
            return InvoiceStatus.PARTIAL
        else:
            return InvoiceStatus.UNPAID

    def _create_purchase_item_and_update_stock(
        self,
        invoice: PurchaseInvoice,
        item_data: Dict[str, Any]
    ):
        """
        Create purchase item entry and update stock with average price calculation.
        """
        item = item_data['item']
        quantity = item_data['quantity']
        unit_price = item_data['unit_price']
        
        # Store values before update for logging
        qty_before = item.total_quantity
        avg_price_before = item.avg_price
        
        logger.debug(
            f"Before update - Item: {item.id}, "
            f"Qty: {qty_before}, Avg Price: {avg_price_before}"
        )
        
        # 1. Create Purchase Item
        purchase_item = PurchaseItem(
            invoice_id=invoice.id,
            item_id=item.id,
            quantity=quantity,
            unit_price=unit_price
        )
        self.db.add(purchase_item)
        logger.debug(f"Purchase item entry created for invoice {invoice.id}")
        
        # 2. Create Stock Ledger Entry (qty_in)
        stock_id = generate_unique_id(self.db, "STK", Stock, length=8)
        stock_entry = Stock(
            id=stock_id,
            item_id=item.id,
            ref_type="PURCHASE",
            ref_id=invoice.id,
            qty_in=quantity,
            qty_out=0,
            unit_price=unit_price
        )
        self.db.add(stock_entry)
        logger.debug(f"Stock ledger entry created: {stock_id}")
        
        # 3. Update Item's Average Price and Total Quantity
        new_avg_price = calculate_weighted_average(
            current_qty=qty_before,
            current_avg_price=avg_price_before,
            new_qty=quantity,
            new_price=unit_price
        )
        
        item.total_quantity += quantity
        item.avg_price = new_avg_price
        self.db.add(item)
        
        logger.info(
            f"Stock updated - Item: {item.name} ({item.id}), "
            f"Qty: {qty_before} → {item.total_quantity}, "
            f"Avg Price: {avg_price_before} → {new_avg_price}"
        )

    def _create_purchase_ledger_entry(
        self,
        supplier_id: int,
        invoice_id: str,
        amount: Decimal
    ):
        """
        Create financial ledger entry for purchase.
        
        For a purchase:
        - Supplier account is DEBITED (you owe them money)
        - This increases your liability to the supplier
        """
        supplier_balance_before = get_user_balance(self.db, supplier_id)
        
        ledger_entry = FinancialLedger(
            user_id=supplier_id,
            ref_type="PURCHASE",
            ref_id=invoice_id,
            debit=amount,  # You owe the supplier
            credit=Decimal('0.00')
        )
        self.db.add(ledger_entry)
        
        supplier_balance_after = supplier_balance_before + amount
        
        logger.info(
            f"Financial ledger entry created - Supplier ID: {supplier_id}, "
            f"Debit: {amount}, "
            f"Balance: {supplier_balance_before} → {supplier_balance_after}"
        )

    def _process_purchase_payment(
        self,
        invoice: PurchaseInvoice,
        supplier_id: int,
        amount: Decimal,
        account_id: str
    ):
        """
        Process payment for purchase and create corresponding ledger entries.
        """
        # Validate payment account
        account = self.db.query(PaymentAccount).filter(
            PaymentAccount.id == account_id
        ).first()
        
        if not account:
            logger.error(f"Payment account not found: {account_id}")
            raise ValueError(f"Payment account {account_id} not found")
        
        logger.info(f"Payment account validated: {account.name} ({account.type})")
        
        # Determine payment type
        if amount >= invoice.total_amount:
            payment_type = PaymentType.FULL
        elif amount > 0:
            payment_type = PaymentType.PARTIAL
        else:
            payment_type = PaymentType.UN_PAID
        
        # Create Payment record with unique ID
        payment_id = generate_unique_id(self.db, "PAY", Payment, length=8)
        
        payment = Payment(
            id=payment_id,
            user_id=supplier_id,
            purchase_invoice_id=invoice.id,
            sale_invoice_id=None,
            amount=amount,
            account_id=account_id,
            payment_type=payment_type
        )
        self.db.add(payment)
        self.db.flush()
        
        logger.debug(f"Payment record created: {payment_id} - Type: {payment_type}")
        
        # Create Financial Ledger entry for payment
        # When we pay the supplier:
        # - Supplier account is CREDITED (reduces our liability)
        supplier_balance_before = get_user_balance(self.db, supplier_id)
        
        payment_ledger = FinancialLedger(
            user_id=supplier_id,
            ref_type="PAYMENT",
            ref_id=payment.id,
            debit=Decimal('0.00'),
            credit=amount  # Reduces what we owe
        )
        self.db.add(payment_ledger)
        
        supplier_balance_after = supplier_balance_before - amount
        
        logger.info(
            f"Financial ledger entry created - "
            f"Credit: {amount}, "
            f"Balance: {supplier_balance_before} → {supplier_balance_after}"
        )

    # ==================== PAYMENT OPERATIONS ====================

    def add_payment_to_purchase(
        self,
        invoice_id: str,
        amount: Decimal,
        account_id: str,
        performed_by_id: Optional[int] = None
    ) -> Payment:
        """
        Add a payment to an existing purchase invoice.
        
        Args:
            invoice_id: Purchase invoice ID
            amount: Payment amount
            account_id: Payment account ID
            performed_by_id: ID of user making the payment
            
        Returns:
            Payment: Created payment record
            
        Process:
            1. Validate invoice exists
            2. Validate payment amount doesn't exceed balance due
            3. Validate payment account exists
            4. Create payment record
            5. Update invoice paid_amount and balance_due
            6. Update invoice payment_status
            7. Create financial ledger entry (credit - you paid supplier)
        """
        logger.info(
            f"Starting payment creation - Invoice: {invoice_id}, "
            f"Amount: {amount}, Account: {account_id}, By: {performed_by_id}"
        )
        
        try:
            # 1. Get and validate invoice
            invoice = self.get_purchase_invoice(invoice_id)
            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                raise ValueError("Purchase invoice not found")
            
            logger.info(
                f"Invoice found: {invoice_id} - "
                f"Total: {invoice.total_amount}, "
                f"Paid: {invoice.paid_amount}, "
                f"Due: {invoice.balance_due}"
            )
            
            # 2. Validate payment amount
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
            
            # 3. Process payment
            self._process_purchase_payment(
                invoice,
                invoice.supplier_id,
                amount,
                account_id
            )
            
            # 4. Update invoice
            old_paid = invoice.paid_amount
            old_due = invoice.balance_due
            old_status = invoice.payment_status
            
            invoice.paid_amount += amount
            invoice.balance_due -= amount
            invoice.payment_status = self._determine_payment_status(
                invoice.total_amount,
                invoice.paid_amount
            )
            
            logger.info(
                f"Invoice updated: {invoice.id} - "
                f"Paid: {old_paid} → {invoice.paid_amount}, "
                f"Due: {old_due} → {invoice.balance_due}, "
                f"Status: {old_status} → {invoice.payment_status}"
            )
            
            self.db.commit()
            
            # Get the created payment
            payment = self.db.query(Payment).filter(
                Payment.purchase_invoice_id == invoice_id
            ).order_by(Payment.created_at.desc()).first()
            
            logger.info(
                f"✅ Payment completed successfully: {payment.id} - "
                f"Invoice: {invoice.id} - "
                f"Amount: {amount} - "
                f"Remaining balance: {invoice.balance_due}"
            )
            
            return payment
            
        except ValueError as ve:
            self.db.rollback()
            logger.error(f"Validation error in payment creation: {str(ve)}")
            raise
            
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Database integrity error in payment creation: {str(ie)}")
            raise ValueError("Failed to create payment due to database constraint.")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in payment creation: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to create payment: {str(e)}")

    def delete_payment(self, payment_id: str) -> bool:
        """
        Delete a payment and reverse the financial entries.
        This will increase the invoice balance_due again.
        """
        logger.info(f"Starting payment deletion: {payment_id}")
        
        try:
            payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                logger.warning(f"Payment not found: {payment_id}")
                return False
            
            # Get invoice
            invoice = None
            if payment.purchase_invoice_id:
                invoice = self.get_purchase_invoice(payment.purchase_invoice_id)
            
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
            ledger_entry = self.db.query(FinancialLedger).filter(
                FinancialLedger.ref_type == "PAYMENT",
                FinancialLedger.ref_id == payment_id
            ).first()
            
            if ledger_entry:
                self.db.delete(ledger_entry)
                logger.debug(f"Financial ledger entry deleted for payment {payment_id}")
            
            # Delete payment
            self.db.delete(payment)
            self.db.commit()
            
            logger.info(
                f"✅ Payment deleted successfully: {payment_id} - "
                f"Invoice {invoice.id} balance restored: {invoice.balance_due}"
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting payment {payment_id}: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to delete payment: {str(e)}")

    # ==================== QUERY METHODS ====================

    def get_purchase_invoice(self, invoice_id: str) -> Optional[PurchaseInvoice]:
        """Get a purchase invoice with all related data."""
        try:
            invoice = (self.db.query(PurchaseInvoice)
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
        self,
        skip: int = 0,
        limit: int = 100,
        supplier_id: Optional[int] = None,
        payment_status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[PurchaseInvoice], int]:
        """Get all purchase invoices with optional filtering."""
        try:
            query = (self.db.query(PurchaseInvoice)
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

             # Date range filtering
            if start_date:
                query = query.filter(cast(PurchaseInvoice.created_at, Date) >= start_date)
                logger.debug(f"Filtering by start_date: {start_date}")
            
            if end_date:
                query = query.filter(cast(PurchaseInvoice.created_at, Date) <= end_date)
                logger.debug(f"Filtering by end_date: {end_date}")
            
            
            total = query.count()
            invoices = query.order_by(PurchaseInvoice.created_at.desc()).offset(skip).limit(limit).all()
            
            logger.info(f"Retrieved {len(invoices)} purchase invoices out of {total} total")
            return invoices, total
            
        except Exception as e:
            logger.error(f"Error fetching purchase invoices: {str(e)}")
            return [], 0

    def get_supplier_purchases(
        self,
        supplier_id: int,
        status: Optional[InvoiceStatus] = None
    ) -> List[PurchaseInvoice]:
        """
        Get all purchases for a supplier, optionally filtered by status.
        """
        invoices, _ = self.get_all_purchase_invoices(
            supplier_id=supplier_id,
            payment_status=status,
            limit=1000  # Get all for supplier
        )
        return invoices

    def get_purchase_invoice_payments(self, invoice_id: str) -> List[Payment]:
        """Get all payments for a purchase invoice."""
        try:
            payments = (self.db.query(Payment)
                       .options(joinedload(Payment.account))
                       .filter(Payment.purchase_invoice_id == invoice_id)
                       .order_by(Payment.created_at.desc())
                       .all())
            
            logger.info(f"Retrieved {len(payments)} payments for invoice {invoice_id}")
            return payments
            
        except Exception as e:
            logger.error(f"Error fetching payments for invoice {invoice_id}: {str(e)}")
            return []

    def get_supplier_balance(self, supplier_id: int) -> Dict[str, Any]:
        """
        Calculate supplier's balance from financial ledger.
        
        Returns:
            Dict with total_debit, total_credit, and balance
            Balance = Debit - Credit (positive means you owe the supplier)
        """
        try:
            logger.info(f"Calculating balance for supplier: {supplier_id}")
            
            result = self.db.query(
                func.sum(FinancialLedger.debit).label('total_debit'),
                func.sum(FinancialLedger.credit).label('total_credit')
            ).filter(
                FinancialLedger.user_id == supplier_id
            ).first()
            
            total_debit = result.total_debit or Decimal('0.00')
            total_credit = result.total_credit or Decimal('0.00')
            balance = total_debit - total_credit
            
            return {
                'supplier_id': supplier_id,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'balance': balance  # Positive = you owe them
            }
            
        except Exception as e:
            logger.error(f"Error calculating supplier balance for {supplier_id}: {str(e)}")
            return {
                'supplier_id': supplier_id,
                'total_debit': Decimal('0.00'),
                'total_credit': Decimal('0.00'),
                'balance': Decimal('0.00')
            }


    def get_all_suppliers_purchase_summary(self) -> List[Dict[str, Any]]:
        """Get comprehensive purchase summary for all suppliers."""
        try:
            logger.info("Generating purchase summary for all suppliers")
            
            # Get all suppliers
            suppliers = self.db.query(User).filter(User.role == UserRole.supplier).all()
            if not suppliers:
                logger.warning("No suppliers found")
                return []
            
            summaries = []

            for supplier in suppliers:
                supplier_id = supplier.id
                
                # Total purchases
                total_purchases = self.db.query(func.sum(PurchaseInvoice.total_amount))\
                    .filter(PurchaseInvoice.supplier_id == supplier_id)\
                    .scalar() or Decimal("0.00")
                
                # Total paid
                total_paid = self.db.query(func.sum(PurchaseInvoice.paid_amount))\
                    .filter(PurchaseInvoice.supplier_id == supplier_id)\
                    .scalar() or Decimal("0.00")
                
                # Outstanding balance from ledger
                balance_info = self.get_supplier_balance(supplier_id)
                outstanding = balance_info.get('balance', Decimal("0.00"))
                
                # Count of invoices by status
                total_invoices = self.db.query(PurchaseInvoice)\
                    .filter(PurchaseInvoice.supplier_id == supplier_id)\
                    .count()
                
                unpaid_count = self.db.query(PurchaseInvoice)\
                    .filter(PurchaseInvoice.supplier_id == supplier_id,
                            PurchaseInvoice.payment_status == InvoiceStatus.UNPAID)\
                    .count()
                
                partial_count = self.db.query(PurchaseInvoice)\
                    .filter(PurchaseInvoice.supplier_id == supplier_id,
                            PurchaseInvoice.payment_status == InvoiceStatus.PARTIAL)\
                    .count()
                
                paid_count = self.db.query(PurchaseInvoice)\
                    .filter(PurchaseInvoice.supplier_id == supplier_id,
                            PurchaseInvoice.payment_status == InvoiceStatus.PAID)\
                    .count()
                
                summaries.append({
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
                })
            
            logger.info(f"Generated purchase summaries for {len(suppliers)} suppliers")
            return summaries

        except Exception as e:
            logger.error(f"Error generating supplier summaries: {str(e)}")
            raise
 

    # ==================== STOCK QUERIES ====================

    def get_item_stock_summary(self, item_id: str) -> Dict[str, Any]:
        """
        Get comprehensive stock summary for an item.
        """
        try:
            item = self.db.query(Item).filter(Item.id == item_id).first()
            
            if not item:
                logger.error(f"Item not found: {item_id}")
                raise ValueError(f"Item {item_id} not found")
            
            # Get total quantity in and out from stock ledger
            stock_summary = self.db.query(
                func.sum(Stock.qty_in).label('total_in'),
                func.sum(Stock.qty_out).label('total_out')
            ).filter(
                Stock.item_id == item_id
            ).first()
            
            total_in = stock_summary.total_in or 0
            total_out = stock_summary.total_out or 0
            
            return {
                'item_id': item_id,
                'item_name': item.name,
                'current_quantity': item.total_quantity,
                'avg_price': item.avg_price,
                'total_value': item.avg_price * item.total_quantity,
                'total_qty_in': total_in,
                'total_qty_out': total_out,
                'unit_type': item.unit_type.value
            }
            
        except Exception as e:
            logger.error(f"Error getting stock summary for item {item_id}: {str(e)}")
            raise

    def get_stock_ledger(
        self,
        item_id: Optional[str] = None,
        ref_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Stock]:
        """
        Get stock ledger entries with optional filters.
        """
        try:
            query = self.db.query(Stock).options(joinedload(Stock.item))
            
            if item_id:
                query = query.filter(Stock.item_id == item_id)
            
            if ref_type:
                query = query.filter(Stock.ref_type == ref_type)
                logger.debug(f"Filtering stock movements by ref_type: {ref_type}")
            
            stock_entries = query.order_by(Stock.created_at.desc()).limit(limit).all()
            
            logger.info(f"Retrieved {len(stock_entries)} stock ledger entries")
            return stock_entries
            
        except Exception as e:
            logger.error(f"Error fetching stock ledger: {str(e)}")
            return []

    def get_item_stock_history(
        self,
        item_id: str,
        limit: int = 50
    ) -> List[Stock]:
        """Get stock movement history for an item."""
        return self.get_stock_ledger(item_id=item_id, limit=limit)

    def get_all_stock_movements(
        self,
        skip: int = 0,
        limit: int = 100,
        ref_type: Optional[str] = None
    ) -> tuple[List[Stock], int]:
        """Get all stock movements with optional filtering."""
        try:
            query = self.db.query(Stock).options(joinedload(Stock.item))
            
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


 