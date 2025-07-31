from app.models.stock import Stock
from decimal import Decimal
def purchase_stock(item_id, quantity, unit_price, total_amount):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0 for purchase")

        # Convert to Decimal to match DB type
    unit_price = Decimal(str(unit_price))
    total_amount = Decimal(str(total_amount))

    stock = Stock.query.filter_by(item_id=item_id).first()
    if stock:
        stock.quantity += quantity
        stock.amount += total_amount
        if stock.quantity <= 0 or stock.amount < 0:
            raise ValueError("Invalid stock update")
        
        stock.unit_price = stock.amount / stock.quantity 
        return stock, False
    else:
        new_stock = Stock(
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            amount=total_amount
        )
        return new_stock, True
    

def sell_stock(item_id, quantity):
    if quantity <= 0:
        raise ValueError("Sale quantity must be greater than 0")

    stock = Stock.query.filter_by(item_id=item_id).first()

    if not stock:
        raise ValueError("Item does not exist in stock")

    if stock.quantity < quantity:
        raise ValueError("Not enough stock available for sale")

    stock.quantity -= quantity

    if stock.quantity > 0:
        stock.amount = stock.unit_price * stock.quantity
    else:
        stock.unit_price = Decimal("0.00")
        stock.amount = Decimal("0.00")
    return stock

