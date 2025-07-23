from app import create_app, db
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.item import Item
from app.models.stock import Stock
from app.models.purchase import Purchase, PaymentStatus
from app.models.payments import Payment, PaymentMethod
from faker import Faker
import uuid
import random
from datetime import datetime, timezone

fake = Faker()
app = create_app()

with app.app_context():
    # Optional: Clear existing data
    db.session.query(Payment).delete()
    db.session.query(Purchase).delete()
    db.session.query(Stock).delete()
    db.session.query(Item).delete()
    db.session.query(Customer).delete()
    db.session.query(Supplier).delete()
    db.session.commit()

    # Seed suppliers and customers
    num_suppliers = random.randint(30, 40)
    num_customers = random.randint(30, 40)

    suppliers = []
    customers = []

    for _ in range(num_suppliers):
        supplier = Supplier(
            supplier_id=str(uuid.uuid4()),
            name=fake.company(),
            phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
            address=fake.address().replace('\n', ', '),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        suppliers.append(supplier)

    for _ in range(num_customers):
        customer = Customer(
            customer_id=str(uuid.uuid4()),
            name=fake.name(),
            phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
            address=fake.address().replace('\n', ', '),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        customers.append(customer)

    db.session.add_all(suppliers + customers)
    db.session.commit()

    # Seed items and stock
    items = []
    stocks = []
    for _ in range(20):
        item = Item(
            name=fake.word().capitalize(),
            type=f"{random.randint(1, 100)}uF"
        )
        db.session.add(item)
        db.session.flush()

        stock = Stock(
            item_id=item.item_id,
            quantity=random.randint(10, 100)
        )
        db.session.add(stock)
        items.append(item)
        stocks.append(stock)

    db.session.commit()

    # Seed purchases and payments
    purchases = []
    payments = []

    for _ in range(30):
        item = random.choice(items)
        supplier = random.choice(suppliers)
        quantity = random.randint(1, 20)
        unit_price = round(random.uniform(50, 500), 2)
        total = round(quantity * unit_price, 2)

        is_paid = random.choice([True, False])
        status = PaymentStatus.PAID if is_paid else PaymentStatus.UNPAID
        purchase_date = datetime.now(timezone.utc)

        purchase = Purchase(
            item_id=item.item_id,
            supplier_id=supplier.supplier_id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total,
            payment_status=status,
            purchase_date=purchase_date,
        )
        db.session.add(purchase)
        db.session.flush()

        if is_paid:
            payment_date = datetime.now(timezone.utc)
            method = random.choice(list(PaymentMethod))
            payment = Payment(
                purchase_id=purchase.purchase_id,
                method=method,
                bank_account=fake.company() if method == PaymentMethod.BANK else None,
                amount_paid=total,
                is_paid=True,
                payment_date=payment_date
            )
            db.session.add(payment)
            payments.append(payment)

        # Update stock
        stock = Stock.query.filter_by(item_id=item.item_id).first()
        if stock:
            stock.quantity += quantity

        purchases.append(purchase)

    db.session.commit()

    print(f"✅ Seeded {len(suppliers)} suppliers")
    print(f"✅ Seeded {len(customers)} customers")
    print(f"✅ Seeded {len(items)} items")
    print(f"✅ Seeded {len(stocks)} stock entries")
    print(f"✅ Seeded {len(purchases)} purchases")
    print(f"✅ Seeded {len(payments)} payments")
