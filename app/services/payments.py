from app.models.payments import Payment, PaymentMethod, BankAccounts
from app.models.purchase import Purchase
from app.models.item import Item
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

def get_all_payments(page=1, limit=10):
    try:
        query = Payment.query.join(Purchase).join(Item)
        paginated = query.paginate(page=page, per_page=limit, error_out=False)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    "payment_id": p.payment_id,
                    "amount_paid": p.amount_paid,
                    "is_paid": p.is_paid,
                    "payment_method": p.method.value if p.method else None,
                    "bank_account": p.bank_account.value if p.method == PaymentMethod.BANK and p.bank_account else None,
                    "payment_date": p.payment_date.isoformat() if p.payment_date else None,

                    # Purchase info
                    "purchase": {
                        "purchase_id": p.purchase.purchase_id,
                        "quantity": p.purchase.quantity,
                        "unit_price": p.purchase.unit_price,
                        "total_amount": p.purchase.total_amount,
                        "payment_status": p.purchase.payment_status.value,
                        "purchase_date": p.purchase.purchase_date.isoformat() if p.purchase.purchase_date else None
                    } if p.purchase else None,

                    # Item info
                    "item": {
                        "item_id": p.purchase.item.item_id,
                        "name": p.purchase.item.name,
                        "type": p.purchase.item.type,
                        "display": f"{p.purchase.item.name} - {p.purchase.item.type}"
                    } if p.purchase and p.purchase.item else None
                }
                for p in paginated.items
            ]
        }

    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred while fetching payments: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
