from app.models.payments import PaymentMethod, BankAccounts
from app.models.purchase import PaymentStatus
def validate_payment_details(data, payment_status):
    """
    Validates payment method and bank account when payment status is PAID.

    Returns:
        (PaymentMethod enum, BankAccount string or None)

    Raises:
        ValueError on invalid input
    """
    method_enum = None
    bank_account_enum = None

    if payment_status == PaymentStatus.PAID:
        method_str = data.get("method")
        if not method_str:
            raise ValueError("Payment method required when marked Paid")

        method_str = method_str.upper()
        if method_str not in PaymentMethod.__members__:
            raise ValueError("Invalid payment method")

        method_enum = PaymentMethod[method_str]

        if method_enum == PaymentMethod.BANK:
            bank_account_str = data.get("bank_account")
            if not bank_account_str:
                raise ValueError("Bank account required for bank payment")

            bank_account_key = bank_account_str.upper().replace(" ", "_")
            if bank_account_key not in BankAccounts.__members__:
                raise ValueError("Invalid bank account")

            bank_account_enum = BankAccounts[bank_account_key].value

    return method_enum, bank_account_enum