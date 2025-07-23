from app.models.stock import  Stock
from app.models.purchase import Purchase,PaymentStatus
from app.models.payments import Payment, PaymentMethod
from app.models.item import Item
from app import db
from datetime import datetime,timezone
from flask import current_app

def get_all_purchases(page, limit):
    paginated = Purchase.query.paginate(page=page, per_page=limit, error_out=False)

    return {
        "total": paginated.total,
        "pages": paginated.pages,
        "current_page": paginated.page,
        "per_page": paginated.per_page,
        "data": [
            {
                "id": p.purchase_id,
                "item_id": p.item_id,
                "supplier_id": p.supplier_id,
                "quantity": p.quantity,
                "unit_price": p.unit_price,
                "total_amount": p.total_amount,
                "payment_status": p.payment_status,
                "purchase_date": p.purchase_date,
                "payment_date": p.payment_date,
                "payment_method": p.payment.method if p.payment else None
            }
            for p in paginated.items
        ]
    }


def create_purchase(data):
    try:
        item_name = data.get("item_name")
        item_type = data.get("item_type")
        quantity = int(data.get("quantity"))
        unit_price = float(data.get("unit_price"))
        total_amount = float(data.get("total_amount"))
        supplier_id = data.get("supplier_id")
        payment_status_str = data.get("payment_status")  # "Paid" or "Unpaid"
        
        # Validate payment status
        if payment_status_str.upper() not in PaymentStatus.__members__:
            raise ValueError("Invalid payment status")
        payment_status = PaymentStatus[payment_status_str.upper()]

        # Check if item exists
        item = Item.query.filter_by(name=item_name, type=item_type).first()
        if not item:
            # Create new item
            item = Item(name=item_name, type=item_type)
            db.session.add(item)
            db.session.flush()  # So we get item.id for stock/purchase

        item_id = item.item_id

        # Create Purchase
        purchase = Purchase(
            item_id=item_id,
            supplier_id=supplier_id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            payment_status=payment_status,
            purchase_date=datetime.now(timezone.utc),  # ← Auto-set
            payment_date=None  # updated later if paid
        )
        db.session.add(purchase)
        db.session.flush()

        # Update or Create Stock
        stock = Stock.query.filter_by(item_id=item_id).first()
        if stock:
            stock.quantity += quantity
        else:
            stock = Stock(item_id=item_id, quantity=quantity)
            db.session.add(stock)

        # Handle Payment if Paid
        if payment_status == PaymentStatus.PAID:
            method_str = data.get("method")
            if not method_str:
                raise ValueError("Payment method required when marked Paid")

            if method_str.upper() not in PaymentMethod.__members__:
                raise ValueError("Invalid payment method")

            method_enum = PaymentMethod[method_str.upper()]
            bank_account = None
            if method_enum == PaymentMethod.BANK:
                bank_account = data.get("bank_account")
                if not bank_account:
                    raise ValueError("Bank account required for bank payment")
                
            payment = Payment(
                purchase_id=purchase.purchase_id,
                method=method_enum,
                bank_account=bank_account,
                amount_paid=total_amount,
                is_paid=True
            )
            purchase.payment_date = datetime.now(timezone.utc)
            db.session.add(payment)

        db.session.commit()

        return {
            "message": "Purchase created successfully",
            "purchase_id": purchase.purchase_id
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating purchase: {str(e)}")
        raise RuntimeError(f"Create purchase failed: {str(e)}")