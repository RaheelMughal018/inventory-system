



from app.models.stock import Stock


def update_or_create_stock(item_id, quantity, unit_price, total_amount):
    stock = Stock.query.filter_by(item_id=item_id).first()
    if stock:
        if quantity < 0:
            if stock.quantity < abs(quantity):
                raise ValueError("Not enough stock available for sale")
        stock.quantity += quantity
        stock.amount += total_amount

        if stock.quantity > 0:
            stock.unit_price = stock.amount / stock.quantity
        else:
            stock.unit_price = 0

        return stock, False
    else:
        if quantity < 0:
            raise ValueError("Cannot create negative stock on sale without existing stock")
        new_stock = Stock(item_id=item_id, quantity=quantity, unit_price=unit_price, amount=total_amount)
        return new_stock, True
