from app.models.purchase_item import Purchase, PaymentStatus
from app.models.payments import Payment, PaymentMethod
from app.models.sales_item import Sale
from app.models.item import Item
from flask import current_app 
from datetime import datetime
from app import db

def apply_filters(query, args, model_type='purchase'):
 

    try:
        id_field = 'supplier_id' if model_type == 'purchase' else 'customer_id'
        entity = Purchase if model_type == 'purchase' else Sale

        target_id = args.get(id_field)
        payment_status = args.get('payment_status')
        item_name = args.get('item_name')
        item_type = args.get('item_type')
        transaction_date = args.get('purchase_date') if model_type == 'purchase' else args.get('sale_date')
        payment_date = args.get('payment_date')
        payment_method = args.get('payment_method')

        if target_id:
            query = query.filter(getattr(entity, id_field) == target_id)

        if payment_status:
            if payment_status.upper() in PaymentStatus.__members__:
                query = query.filter(Purchase.payment_status == PaymentStatus[payment_status.upper()])


        if item_name:
            query = query.filter(Item.name.ilike(f"%{item_name}%"))

        if item_type:
            query = query.filter(Item.type.ilike(f"%{item_type}%"))

        if transaction_date:
            try:
                date_obj = datetime.fromisoformat(transaction_date)
                column = entity.purchase_date if model_type == 'purchase' else entity.sale_date
                query = query.filter(column.cast(db.Date) == date_obj.date())
            except ValueError:
                current_app.logger.warning("Invalid transaction_date format")

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
        current_app.logger.exception(f"Error in apply_filters: {str(e)}")
        return query
