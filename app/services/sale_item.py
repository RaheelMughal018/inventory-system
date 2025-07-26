from app.models.stock import Stock
from app.models.sales_item import Sale, PaymentStatus
from app.models.payments import Payment, PaymentMethod, BankAccounts
from app.models.customer import Customer
from app.models.item import Item
from sqlalchemy.exc import SQLAlchemyError
from app.utils.purchase_filterations import apply_purchase_filters
from app.utils.payment_validation import validate_payment_details
from app.utils.update_or_create_stock import update_or_create_stock

from app import db
from datetime import datetime, timezone
from flask import current_app, request


def get_all_sales(page, limit):
    try:
        query = (
            Sale.query
            .join(Item, Item.item_id == Sale.item_id)
            .join(Customer, Customer.customer_id == Sale.customer_id)
            .outerjoin(Payment, Payment.sale_id == Sale.sale_id)
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
                    "sale_id": s.sale_id,
                    "quantity": s.quantity,
                    "unit_price": s.unit_price,
                    "total_amount": s.total_amount,
                    "payment_status": s.payment_status.value,
                    "sale_date": s.sale_date,
                    "payment_date": s.payment.payment_date if s.payment else None,
                    "payment_method": s.payment.method.value if s.payment else None,
                    "bank_account": (
                        s.payment.bank_account.value
                        if s.payment and s.payment.method == PaymentMethod.BANK and s.payment.bank_account
                        else None
                    ),
                    "item": {
                        "id": s.item.item_id,
                        "name": s.item.name,
                        "type": s.item.type,
                        "display": f"{s.item.name} - {s.item.type}"
                    },
                    "customer": {
                        "id": s.customer.customer_id,
                        "name": s.customer.name
                    }
                }
                for s in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")


def create_sale(data):
    try:
        item_name = data.get("item_name")
        item_type = data.get("item_type")
        quantity = int(data.get("quantity"))
        total_amount = float(data.get("total_amount"))
        customer_id = data.get("customer_id")
        payment_status_str = data.get("payment_status")

        if payment_status_str.upper() not in PaymentStatus.__members__:
            raise ValueError("Invalid payment status")
        payment_status = PaymentStatus[payment_status_str.upper()]

        item = Item.query.filter_by(name=item_name, type=item_type).first()
        if not item:
            item = Item(name=item_name, type=item_type)
            db.session.add(item)
            db.session.flush()

        item_id = item.item_id
        unit_price = total_amount / quantity if quantity > 0 else 0

        sale = Sale(
            item_id=item_id,
            customer_id=customer_id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            payment_status=payment_status,
            sale_date=datetime.now(timezone.utc),
        )
        db.session.add(sale)
        db.session.flush()

        try:
            stock, is_new = update_or_create_stock(item_id, -quantity)
            if is_new:
                db.session.add(stock)
        except ValueError as ve:
            raise RuntimeError(f"Stock error: {str(ve)}")

        payment = None
        if payment_status == PaymentStatus.PAID:
            method_str = data.get("payment_method")
            if not method_str or method_str.upper() not in PaymentMethod.__members__:
                raise ValueError("Invalid or missing payment method for PAID sale")

            method_enum = PaymentMethod[method_str.upper()]
            bank_account_enum = None

            if method_enum == PaymentMethod.BANK:
                bank_account_str = data.get("bank_account")
                if not bank_account_str or bank_account_str.upper() not in BankAccounts.__members__:
                    raise ValueError("Missing or invalid bank account for BANK payment")
                bank_account_enum = BankAccounts[bank_account_str.upper()]

            payment = Payment(
                sale_id=sale.sale_id,
                method=method_enum,
                bank_account=bank_account_enum,
                amount_paid=total_amount,
                is_paid=True,
                payment_date=datetime.now(timezone.utc)
            )
            db.session.add(payment)

        db.session.commit()

        customer = Customer.query.get(customer_id)
        return {
            "message": "Sale created successfully",
            "sale_id": sale.sale_id,
            "data": {
                "id": sale.sale_id,
                "quantity": sale.quantity,
                "unit_price": sale.unit_price,
                "total_amount": sale.total_amount,
                "payment_status": sale.payment_status.value,
                "sale_date": sale.sale_date,
                "payment_date": payment.payment_date if payment else None,
                "payment_method": payment.method.value if payment else None,
                "bank_account": payment.bank_account.value if payment and payment.method == PaymentMethod.BANK else None,
                "item": {
                    "id": item.item_id,
                    "name": item.name,
                    "type": item.type,
                    "display": f"{item.name} - {item.type}"
                },
                "customer": {
                    "id": customer.customer_id,
                    "name": customer.name
                }
            }
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating sale: {str(e)}")
        raise RuntimeError(f"Create sale failed: {str(e)}")


def update_sale_status(sale_id, data):
    try:
        sale = Sale.query.get(sale_id)
        if not sale:
            raise ValueError("Sale not found")

        if sale.payment_status == PaymentStatus.PAID:
            raise ValueError("Sale is already marked as PAID")

        payment_status_str = data.get("payment_status")
        if not payment_status_str or payment_status_str.upper() != "PAID":
            raise ValueError("Only status update to PAID is allowed")

        payment_method_str = data.get("payment_method")
        if not payment_method_str or payment_method_str.upper() not in PaymentMethod.__members__:
            raise ValueError("Invalid or missing payment method")

        method_enum = PaymentMethod[payment_method_str.upper()]
        bank_account_enum = None

        if method_enum == PaymentMethod.BANK:
            bank_account_str = data.get("bank_account")
            if not bank_account_str or bank_account_str.upper() not in BankAccounts.__members__:
                raise ValueError("Missing or invalid bank account for BANK payment")
            bank_account_enum = BankAccounts[bank_account_str.upper()]

        payment = Payment(
            sale_id=sale.sale_id,
            method=method_enum,
            bank_account=bank_account_enum,
            amount_paid=sale.total_amount,
            is_paid=True,
            payment_date=datetime.now(timezone.utc)
        )
        db.session.add(payment)

        sale.payment_status = PaymentStatus.PAID
        db.session.commit()

        return {
            "message": "Sale status updated to PAID successfully",
            "sale_id": sale.sale_id,
            "payment_method": method_enum.value,
            "bank_account": bank_account_enum.value if bank_account_enum else None,
            "payment_date": payment.payment_date
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating sale status: {str(e)}")
        raise RuntimeError(f"Update sale status failed: {str(e)}")
