from app.models.stock import  Stock
from app.models.purchase import Purchase,PaymentStatus
from app.models.payments import Payment, PaymentMethod,BankAccounts
from app.models.supplier import Supplier
from app.models.item import Item
from sqlalchemy.exc import SQLAlchemyError
from app.utils.purchase_filterations import apply_purchase_filters
from app.utils.payment_validation import validate_payment_details
from app.utils.update_or_create_stock import update_or_create_stock

from app import db
from datetime import datetime,timezone
from flask import current_app, request

def get_all_purchases(page, limit):
    try:  
        query = (
            Purchase.query
            .join(Item, Item.item_id == Purchase.item_id)
            .join(Supplier, Supplier.supplier_id == Purchase.supplier_id)
            .outerjoin(Payment, Payment.purchase_id == Purchase.purchase_id)
        )
        query = apply_purchase_filters(query, request.args)
        paginated = query.paginate(page=page, per_page=limit, error_out=False)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    "id": p.purchase_id,
                    "quantity": p.quantity,
                    "unit_price": p.unit_price,
                    "total_amount": p.total_amount,
                    "payment_status": p.payment_status.value,
                    "purchase_date": p.purchase_date,
                    "payment_date": p.payment.payment_date if p.payment else None,
                    "payment_method": p.payment.method.value if p.payment else None,

                    # Full item info
                    "item": {
                        "id": p.item.item_id,
                        "name": p.item.name,
                        "type": p.item.type,
                        "display": f"{p.item.name} - {p.item.type}"
                    },

                    # Full supplier info
                    "supplier": {
                        "id": p.supplier.supplier_id,
                        "name": p.supplier.name
                    }
                }
                for p in paginated.items
            ]
        }
    except SQLAlchemyError as e:
            current_app.logger.exception(f"Database error occurred {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}")


def create_purchase(data):
    try:
        item_name = data.get("item_name")
        item_type = data.get("item_type")
        quantity = int(data.get("quantity"))
        total_amount = float(data.get("total_amount"))
        supplier_id = data.get("supplier_id")
        payment_status_str = data.get("payment_status")  
        
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
        calculate_unit_price = total_amount / quantity if quantity > 0 else 0
        # Create Purchase
        purchase = Purchase(
            item_id=item_id,
            supplier_id=supplier_id,
            quantity=quantity,
            unit_price=calculate_unit_price,
            total_amount=total_amount,
            payment_status=payment_status,
            purchase_date=datetime.now(timezone.utc),  # ← Auto-set
        )
        db.session.add(purchase)
        db.session.flush()

        # Update or Create Stock
        stock, is_new = update_or_create_stock(item_id, quantity)
        if is_new:
            db.session.add(stock) 

         # Validate and create Payment if status is Paid
        method_enum, bank_account_enum = validate_payment_details(data, payment_status)

        if payment_status == PaymentStatus.PAID:
            payment = Payment(
                purchase_id=purchase.purchase_id,
                method=method_enum,
                bank_account=bank_account_enum,
                amount_paid=total_amount,
                is_paid=True,
                payment_date=datetime.now(timezone.utc)
            ) 
            db.session.add(payment)
            db.session.commit()

        supplier = Supplier.query.get(supplier_id)
        return {
            "message": "Purchase created successfully",
            "purchase_id": purchase.purchase_id,
            "data": {
                "id": purchase.purchase_id,
                "quantity": purchase.quantity,
                "unit_price": purchase.unit_price,
                "total_amount": purchase.total_amount,
                "payment_status": purchase.payment_status.value,
                "purchase_date": purchase.purchase_date,
                "payment_date": payment.payment_date if payment else None,
                "payment_method": payment.method.value if payment else None,
                "item": {
                    "id": item.item_id,
                    "name": item.name,
                    "type": item.type,
                    "display": f"{item.name} - {item.type}"
                },
                "supplier": {
                    "id": supplier.supplier_id,
                    "name": supplier.name
                }
            }
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating purchase: {str(e)}")
        raise RuntimeError(f"Create purchase failed: {str(e)}")