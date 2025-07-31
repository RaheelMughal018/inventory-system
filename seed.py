from app import create_app, db
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.item import Item
from app.models.sales_item import Sale
from app.models.stock import Stock
from app.models.purchase_item import Purchase, PaymentStatus
from app.models.payments import Payment, PaymentMethod, BankAccounts
from faker import Faker
import uuid
import random
from datetime import datetime, timezone

fake = Faker()
app = create_app()

def update_or_create_stock(item_id, quantity_delta, unit_price, total_amount_delta):
    stock = Stock.query.filter_by(item_id=item_id).first()
    if stock:
        stock.quantity += quantity_delta
        stock.amount += total_amount_delta
        stock.unit_price = stock.amount / stock.quantity if stock.quantity > 0 else 0
        return stock, False
    else:
        new_stock = Stock(
            item_id=item_id,
            quantity=quantity_delta,
            unit_price=unit_price,
            amount=total_amount_delta
        )
        return new_stock, True

with app.app_context():
    try:
        print("🔄 Clearing existing data...")
        db.session.query(Payment).delete()
        db.session.query(Purchase).delete()
        db.session.query(Sale).delete()
        db.session.query(Stock).delete()
        db.session.query(Item).delete()
        db.session.query(Customer).delete()
        db.session.query(Supplier).delete()
        db.session.commit()
        print("✅ Data cleared.")

        print("🔄 Creating suppliers and customers...")
        suppliers = []
        customers = []

        for _ in range(random.randint(30, 40)):
            suppliers.append(Supplier(
                supplier_id=str(uuid.uuid4()),
                name=fake.company(),
                phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
                address=fake.address().replace('\n', ', '),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ))

        for _ in range(random.randint(30, 40)):
            customers.append(Customer(
                customer_id=str(uuid.uuid4()),
                name=fake.name(),
                phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
                address=fake.address().replace('\n', ', '),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ))

        db.session.add_all(suppliers + customers)
        db.session.commit()
        print(f"✅ Seeded {len(suppliers)} suppliers")
        print(f"✅ Seeded {len(customers)} customers")

        print("🔄 Creating items and stock...")
        items = []
        for _ in range(20):
            item = Item(
                name=fake.word().capitalize(),
                type=f"{random.randint(1, 100)}uF"
            )
            db.session.add(item)
            db.session.flush()
            quantity = random.randint(10, 100)
            unit_price = round(random.uniform(20, 100), 2)
            amount = round(quantity * unit_price, 2)
            db.session.add(Stock(item_id=item.item_id, quantity=quantity, unit_price=unit_price, amount=amount))
            items.append(item)

        db.session.commit()
        print(f"✅ Seeded {len(items)} items and stock entries")

        print("🔄 Creating purchases and payments...")
        purchases = []
        payments = []

        for _ in range(30):
            item = random.choice(items)
            supplier = random.choice(suppliers)
            quantity = random.randint(1, 20)
            unit_price = round(random.uniform(50, 500), 2)
            total = round(quantity * unit_price, 2)
            status = PaymentStatus.UNPAID
            payment = None

            if random.choice([True, False]):
                method = random.choice(list(PaymentMethod))
                bank_account = random.choice(list(BankAccounts)) if method == PaymentMethod.BANK else None
                payment = Payment(
                    method=method,
                    bank_account=bank_account,
                    amount_paid=total,
                    is_paid=True,
                    payment_date=datetime.now(timezone.utc)
                )
                status = PaymentStatus.PAID
                print(f"💰 Paid purchase via {method.value}{' | Bank: ' + bank_account.value if bank_account else ''}")

            purchase = Purchase(
                item_id=item.item_id,
                supplier_id=supplier.supplier_id,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total,
                payment_status=status,
                purchase_date=datetime.now(timezone.utc)
            )
            db.session.add(purchase)
            db.session.flush()

            if payment:
                payment.purchase_id = purchase.purchase_id
                db.session.add(payment)
                payments.append(payment)

            stock, is_new = update_or_create_stock(item.item_id, quantity, unit_price, total)
            if is_new:
                db.session.add(stock)

            purchases.append(purchase)

        db.session.commit()
        print(f"✅ Seeded {len(purchases)} purchases")
        print(f"✅ Seeded {len(payments)} payments")

        print("🔄 Creating sales and payments...")
        sales = []
        sale_payments = []

        for _ in range(30):
            item = random.choice(items)
            customer = random.choice(customers)
            stock = Stock.query.filter_by(item_id=item.item_id).first()
            if not stock or stock.quantity < 1:
                continue

            quantity = random.randint(1, min(stock.quantity, 10))
            unit_price = round(random.uniform(100, 600), 2)
            total = round(quantity * unit_price, 2)
            status = PaymentStatus.UNPAID.value
            payment = None

            if random.choice([True, False]):
                method = random.choice(list(PaymentMethod))
                bank_account = random.choice(list(BankAccounts)) if method == PaymentMethod.BANK else None
                payment = Payment(
                    method=method,
                    bank_account=bank_account,
                    amount_paid=total,
                    is_paid=True,
                    payment_date=datetime.now(timezone.utc)
                )
                status = PaymentStatus.PAID.value
                print(f"📟 Paid sale via {method.value}{' | Bank: ' + bank_account.value if bank_account else ''}")

            sale = Sale(
                item_id=item.item_id,
                customer_id=customer.customer_id,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total,
                payment_status=status,
                sale_date=datetime.now(timezone.utc)
            )
            db.session.add(sale)
            db.session.flush()

            if payment:
                payment.sale_id = sale.sale_id
                db.session.add(payment)
                sale_payments.append(payment)

            stock, is_new = update_or_create_stock(item.item_id, -quantity, unit_price, -total)
            if is_new:
                db.session.add(stock)

            sales.append(sale)

        db.session.commit()
        print(f"✅ Seeded {len(sales)} sales")
        print(f"✅ Seeded {len(sale_payments)} sale payments")
        print("🎉 All data seeded successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ SEEDING FAILED: {e}")
