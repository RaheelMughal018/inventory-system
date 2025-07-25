



from app.models.stock import Stock


def update_or_create_stock(item_id, quantity):
    """
    Update existing stock by adding quantity or create a new stock entry.

    Args:
        item_id (str): The ID of the item.
        quantity (int): Quantity to add.

    Returns:
        Stock: The updated or newly created stock instance.
    """
    stock = Stock.query.filter_by(item_id=item_id).first()
    if stock:
        stock.quantity += quantity
        return stock, False
    else:
        new_stock = Stock(item_id=item_id, quantity=quantity)
        return new_stock, True
