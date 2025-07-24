from app.models.purchase import Purchase, PaymentStatus
from app.models.payments import Payment, PaymentMethod
from app.models.item import Item
from flask import current_app 
from datetime import datetime
from app import db


def apply_purchase_filters(query, args):
    try:
        supplier_id = args.get('supplier_id')
        payment_status = args.get('payment_status')
        item_name = args.get('item_name')
        item_type = args.get('item_type')
        purchase_date = args.get('purchase_date')
        payment_date = args.get('payment_date')
        payment_method = args.get('payment_method')

        if supplier_id:
            query = query.filter(Purchase.supplier_id == supplier_id)

        if payment_status:
            if payment_status.upper() in PaymentStatus.__members__:
                query = query.filter(Purchase.payment_status == PaymentStatus[payment_status.upper()])

        if item_name:
            query = query.filter(Item.name.ilike(f"%{item_name}%"))

        if item_type:
            query = query.filter(Item.type.ilike(f"%{item_type}%"))

        if purchase_date:
            try:
                date_obj = datetime.fromisoformat(purchase_date)
                query = query.filter(Purchase.purchase_date.cast(db.Date) == date_obj.date())
            except ValueError:
                current_app.logger.warning("Invalid purchase_date format")

        if payment_date:
            try:
                date_obj = datetime.fromisoformat(payment_date)
                query = query.filter(Payment.payment_date.cast(db.Date) == date_obj.date())
            except ValueError:
                current_app.logger.warning("Invalid payment_date format")

        if payment_method:
            if payment_method.upper() in PaymentMethod.__members__:
                query = query.filter(Payment.method == PaymentMethod[payment_method.upper()])

        return query

    except Exception as e:
        current_app.logger.exception(f"Error in apply_purchase_filters: {str(e)}")
        return query