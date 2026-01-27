"""
Purchase Module Utilities and Integration Examples
Additional helper functions and integration patterns
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.user import User
from app.models.item_category import Item
from app.models.stock import PurchaseInvoice, PurchaseItem, Stock
from app.models.payment import Payment, PaymentAccount
from app.models.financial_ledger import FinancialLedger


# ============================================================================
# Reporting and Analytics Utilities
# ============================================================================

class PurchaseAnalytics:
    """Advanced analytics and reporting for purchases."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_purchase_summary(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get overall purchase summary with statistics.
        
        Returns:
            Dict with total purchases, amounts, unique suppliers/items
        """
        query = self.db.query(PurchaseInvoice)
        
        if date_from:
            query = query.filter(PurchaseInvoice.created_at >= date_from)
        if date_to:
            query = query.filter(PurchaseInvoice.created_at <= date_to)
        
        invoices = query.all()
        
        total_amount = sum(inv.total_amount for inv in invoices)
        total_paid = sum(inv.paid_amount for inv in invoices)
        total_due = sum(inv.balance_due for inv in invoices)
        
        unique_suppliers = len(set(inv.supplier_id for inv in invoices))
        
        # Get unique items across all purchases
        item_ids = set()
        for inv in invoices:
            for item in inv.items:
                item_ids.add(item.item_id)
        
        return {
            "total_purchases": len(invoices),
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_due": total_due,
            "unique_suppliers": unique_suppliers,
            "unique_items": len(item_ids),
            "date_from": date_from,
            "date_to": date_to
        }
    
    def get_supplier_statistics(
        self,
        supplier_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific supplier.
        """
        query = self.db.query(PurchaseInvoice).filter(
            PurchaseInvoice.supplier_id == supplier_id
        )
        
        if date_from:
            query = query.filter(PurchaseInvoice.created_at >= date_from)
        if date_to:
            query = query.filter(PurchaseInvoice.created_at <= date_to)
        
        invoices = query.all()
        
        if not invoices:
            return {
                "supplier_id": supplier_id,
                "total_purchases": 0,
                "total_amount": Decimal('0.00'),
                "total_paid": Decimal('0.00'),
                "balance_due": Decimal('0.00'),
                "last_purchase_date": None
            }
        
        supplier = self.db.query(User).filter(User.id == supplier_id).first()
        
        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier.name if supplier else "Unknown",
            "total_purchases": len(invoices),
            "total_amount": sum(inv.total_amount for inv in invoices),
            "total_paid": sum(inv.paid_amount for inv in invoices),
            "balance_due": sum(inv.balance_due for inv in invoices),
            "last_purchase_date": max(inv.created_at for inv in invoices)
        }
    
    def get_item_purchase_history(
        self,
        item_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get purchase history for a specific item.
        
        Returns list of purchases with dates, quantities, and prices.
        """
        purchase_items = self.db.query(PurchaseItem).filter(
            PurchaseItem.item_id == item_id
        ).order_by(
            PurchaseItem.id.desc()
        ).limit(limit).all()
        
        history = []
        for pi in purchase_items:
            history.append({
                "invoice_id": pi.invoice_id,
                "date": pi.invoice.created_at if pi.invoice else None,
                "supplier": pi.invoice.supplier.name if pi.invoice and pi.invoice.supplier else "Unknown",
                "quantity": pi.quantity,
                "unit_price": pi.unit_price,
                "total_value": pi.quantity * pi.unit_price
            })
        
        return history
    
    def get_price_trend(
        self,
        item_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get price trend for an item over specified days.
        
        Returns list of purchases with dates and prices for charting.
        """
        date_threshold = datetime.now() - timedelta(days=days)
        
        purchase_items = self.db.query(PurchaseItem).join(
            PurchaseInvoice
        ).filter(
            and_(
                PurchaseItem.item_id == item_id,
                PurchaseInvoice.created_at >= date_threshold
            )
        ).order_by(PurchaseInvoice.created_at.asc()).all()
        
        trend = []
        for pi in purchase_items:
            trend.append({
                "date": pi.invoice.created_at.strftime("%Y-%m-%d"),
                "unit_price": float(pi.unit_price),
                "quantity": pi.quantity
            })
        
        return trend
    
    def get_top_suppliers_by_volume(
        self,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top suppliers by purchase volume.
        """
        query = self.db.query(
            User.id,
            User.name,
            func.count(PurchaseInvoice.id).label('purchase_count'),
            func.sum(PurchaseInvoice.total_amount).label('total_amount')
        ).join(
            PurchaseInvoice, User.id == PurchaseInvoice.supplier_id
        )
        
        if date_from:
            query = query.filter(PurchaseInvoice.created_at >= date_from)
        if date_to:
            query = query.filter(PurchaseInvoice.created_at <= date_to)
        
        results = query.group_by(
            User.id, User.name
        ).order_by(
            func.sum(PurchaseInvoice.total_amount).desc()
        ).limit(limit).all()
        
        return [
            {
                "supplier_id": r.id,
                "supplier_name": r.name,
                "purchase_count": r.purchase_count,
                "total_amount": r.total_amount
            }
            for r in results
        ]
    
    def get_top_purchased_items(
        self,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most purchased items by quantity.
        """
        query = self.db.query(
            Item.id,
            Item.name,
            func.sum(PurchaseItem.quantity).label('total_quantity'),
            func.sum(PurchaseItem.quantity * PurchaseItem.unit_price).label('total_value')
        ).join(
            PurchaseItem, Item.id == PurchaseItem.item_id
        ).join(
            PurchaseInvoice, PurchaseItem.invoice_id == PurchaseInvoice.id
        )
        
        if date_from:
            query = query.filter(PurchaseInvoice.created_at >= date_from)
        if date_to:
            query = query.filter(PurchaseInvoice.created_at <= date_to)
        
        results = query.group_by(
            Item.id, Item.name
        ).order_by(
            func.sum(PurchaseItem.quantity).desc()
        ).limit(limit).all()
        
        return [
            {
                "item_id": r.id,
                "item_name": r.name,
                "total_quantity": r.total_quantity,
                "total_value": r.total_value
            }
            for r in results
        ]


# ============================================================================
# Payment Utilities
# ============================================================================

class PaymentUtilities:
    """Helper functions for payment operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_outstanding_invoices(
        self,
        supplier_id: Optional[int] = None
    ) -> List[PurchaseInvoice]:
        """
        Get all invoices with outstanding balance.
        """
        query = self.db.query(PurchaseInvoice).filter(
            PurchaseInvoice.balance_due > 0
        )
        
        if supplier_id:
            query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
        
        return query.order_by(PurchaseInvoice.created_at.asc()).all()
    
    def get_overdue_invoices(
        self,
        days: int = 30,
        supplier_id: Optional[int] = None
    ) -> List[PurchaseInvoice]:
        """
        Get invoices overdue by specified days.
        """
        threshold_date = datetime.now() - timedelta(days=days)
        
        query = self.db.query(PurchaseInvoice).filter(
            and_(
                PurchaseInvoice.balance_due > 0,
                PurchaseInvoice.created_at <= threshold_date
            )
        )
        
        if supplier_id:
            query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
        
        return query.order_by(PurchaseInvoice.created_at.asc()).all()
    
    def get_payment_account_summary(
        self,
        account_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get summary of payments through a specific account.
        """
        query = self.db.query(Payment).filter(
            Payment.account_id == account_id
        )
        
        if date_from:
            query = query.filter(Payment.created_at >= date_from)
        if date_to:
            query = query.filter(Payment.created_at <= date_to)
        
        payments = query.all()
        
        # Separate purchase and sale payments
        purchase_payments = [p for p in payments if p.purchase_invoice_id]
        sale_payments = [p for p in payments if p.sale_invoice_id]
        
        account = self.db.query(PaymentAccount).filter(
            PaymentAccount.id == account_id
        ).first()
        
        return {
            "account_id": account_id,
            "account_name": account.name if account else "Unknown",
            "account_type": account.type.value if account else None,
            "total_payments": len(payments),
            "purchase_payments_count": len(purchase_payments),
            "purchase_payments_total": sum(p.amount for p in purchase_payments),
            "sale_payments_count": len(sale_payments),
            "sale_payments_total": sum(p.amount for p in sale_payments)
        }


# ============================================================================
# Stock Management Utilities
# ============================================================================

class StockUtilities:
    """Helper functions for stock management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_low_stock_items(
        self,
        threshold: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get items with stock below threshold.
        """
        items = self.db.query(Item).filter(
            Item.total_quantity <= threshold
        ).all()
        
        return [
            {
                "item_id": item.id,
                "item_name": item.name,
                "current_quantity": item.total_quantity,
                "avg_price": item.avg_price,
                "unit_type": item.unit_type.value
            }
            for item in items
        ]
    
    def get_zero_stock_items(self) -> List[Item]:
        """Get items with zero stock."""
        return self.db.query(Item).filter(
            Item.total_quantity == 0
        ).all()
    
    def calculate_inventory_value(self) -> Dict[str, Any]:
        """
        Calculate total inventory value across all items.
        """
        items = self.db.query(Item).all()
        
        total_value = Decimal('0.00')
        item_count = 0
        total_quantity = 0
        
        for item in items:
            item_value = item.avg_price * item.total_quantity
            total_value += item_value
            if item.total_quantity > 0:
                item_count += 1
            total_quantity += item.total_quantity
        
        return {
            "total_value": total_value,
            "total_items": len(items),
            "items_in_stock": item_count,
            "total_quantity": total_quantity
        }
    
    def get_stock_movement_summary(
        self,
        item_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get summary of stock movements for an item.
        """
        query = self.db.query(Stock).filter(Stock.item_id == item_id)
        
        if date_from:
            query = query.filter(Stock.created_at >= date_from)
        if date_to:
            query = query.filter(Stock.created_at <= date_to)
        
        entries = query.all()
        
        total_in = sum(e.qty_in for e in entries)
        total_out = sum(e.qty_out for e in entries)
        
        item = self.db.query(Item).filter(Item.id == item_id).first()
        
        return {
            "item_id": item_id,
            "item_name": item.name if item else "Unknown",
            "total_qty_in": total_in,
            "total_qty_out": total_out,
            "net_change": total_in - total_out,
            "current_stock": item.total_quantity if item else 0,
            "movements_count": len(entries)
        }


# ============================================================================
# Integration Examples
# ============================================================================

def example_monthly_purchase_report(db: Session):
    """
    Example: Generate monthly purchase report
    """
    analytics = PurchaseAnalytics(db)
    
    # Get current month
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get summary
    summary = analytics.get_purchase_summary(
        date_from=month_start,
        date_to=now
    )
    
    # Get top suppliers
    top_suppliers = analytics.get_top_suppliers_by_volume(
        limit=5,
        date_from=month_start,
        date_to=now
    )
    
    # Get top items
    top_items = analytics.get_top_purchased_items(
        limit=5,
        date_from=month_start,
        date_to=now
    )
    
    report = {
        "period": f"{month_start.strftime('%B %Y')}",
        "summary": summary,
        "top_suppliers": top_suppliers,
        "top_items": top_items
    }
    
    return report


def example_supplier_reconciliation(db: Session, supplier_id: int):
    """
    Example: Reconcile supplier account
    """
    analytics = PurchaseAnalytics(db)
    payment_utils = PaymentUtilities(db)
    
    # Get supplier stats
    stats = analytics.get_supplier_statistics(supplier_id)
    
    # Get outstanding invoices
    outstanding = payment_utils.get_outstanding_invoices(supplier_id)
    
    # Get overdue invoices
    overdue = payment_utils.get_overdue_invoices(days=30, supplier_id=supplier_id)
    
    reconciliation = {
        "supplier_id": supplier_id,
        "statistics": stats,
        "outstanding_invoices": [
            {
                "invoice_id": inv.id,
                "date": inv.created_at,
                "amount": inv.total_amount,
                "paid": inv.paid_amount,
                "due": inv.balance_due
            }
            for inv in outstanding
        ],
        "overdue_invoices": [
            {
                "invoice_id": inv.id,
                "date": inv.created_at,
                "days_overdue": (datetime.now() - inv.created_at).days,
                "amount_due": inv.balance_due
            }
            for inv in overdue
        ]
    }
    
    return reconciliation


def example_inventory_valuation(db: Session):
    """
    Example: Get current inventory valuation
    """
    stock_utils = StockUtilities(db)
    
    # Overall valuation
    valuation = stock_utils.calculate_inventory_value()
    
    # Low stock items
    low_stock = stock_utils.get_low_stock_items(threshold=20)
    
    # Zero stock items
    zero_stock = stock_utils.get_zero_stock_items()
    
    report = {
        "valuation": valuation,
        "alerts": {
            "low_stock_items": low_stock,
            "out_of_stock_items": [
                {
                    "item_id": item.id,
                    "item_name": item.name
                }
                for item in zero_stock
            ]
        }
    }
    
    return report


def example_price_analysis(db: Session, item_id: str):
    """
    Example: Analyze price trends for an item
    """
    analytics = PurchaseAnalytics(db)
    
    # Get purchase history
    history = analytics.get_item_purchase_history(item_id, limit=20)
    
    # Get price trend
    trend = analytics.get_price_trend(item_id, days=90)
    
    # Calculate statistics
    if history:
        prices = [h['unit_price'] for h in history]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        analysis = {
            "item_id": item_id,
            "purchase_count": len(history),
            "avg_purchase_price": avg_price,
            "min_price": min_price,
            "max_price": max_price,
            "price_variance": max_price - min_price,
            "recent_purchases": history[:5],
            "price_trend_90_days": trend
        }
    else:
        analysis = {
            "item_id": item_id,
            "message": "No purchase history found"
        }
    
    return analysis


# ============================================================================
# Batch Operations
# ============================================================================

def batch_create_purchases(
    db: Session,
    purchases: List[Dict[str, Any]]
) -> List[PurchaseInvoice]:
    """
    Create multiple purchases in a batch.
    
    Args:
        purchases: List of purchase data dicts
        
    Returns:
        List of created invoices
    """
    from app.services.purchase_service import PurchaseService
    
    service = PurchaseService(db)
    created_invoices = []
    
    try:
        for purchase_data in purchases:
            invoice = service.create_purchase(**purchase_data)
            created_invoices.append(invoice)
        
        return created_invoices
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Batch purchase creation failed: {str(e)}")


def batch_process_payments(
    db: Session,
    payments: List[Dict[str, Any]]
) -> List[Payment]:
    """
    Process multiple payments in a batch.
    
    Args:
        payments: List of payment data dicts with invoice_id, amount, account_id
        
    Returns:
        List of created payments
    """
    from app.services.purchase_service import PurchaseService
    
    service = PurchaseService(db)
    created_payments = []
    
    try:
        for payment_data in payments:
            payment = service.add_payment_to_purchase(**payment_data)
            created_payments.append(payment)
        
        return created_payments
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Batch payment processing failed: {str(e)}")