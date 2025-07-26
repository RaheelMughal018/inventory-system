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

with app.app_context():
    try:
        print("🔄 Clearing existing data...")
        db.session.query(Payment).delete()
        db.session.query(Purchase).delete()
        db.session.query(Stock).delete()
        db.session.query(Item).delete()
        db.session.query(Customer).delete()
        db.session.query(Supplier).delete()
        db.session.commit()
        print("✅ Data cleared.")

        # Seed suppliers and customers
        print("🔄 Creating suppliers and customers...")
        suppliers = []
        customers = []

        for _ in range(random.randint(30, 40)):
            try:
                supplier = Supplier(
                    supplier_id=str(uuid.uuid4()),
                    name=fake.company(),
                    phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
                    address=fake.address().replace('\n', ', '),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                suppliers.append(supplier)
            except Exception as e:
                print(f"❌ Failed to create supplier: {e}")

        for _ in range(random.randint(30, 40)):
            try:
                customer = Customer(
                    customer_id=str(uuid.uuid4()),
                    name=fake.name(),
                    phone=''.join(filter(str.isdigit, fake.phone_number()))[:20],
                    address=fake.address().replace('\n', ', '),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                customers.append(customer)
            except Exception as e:
                print(f"❌ Failed to create customer: {e}")

        db.session.add_all(suppliers + customers)
        db.session.commit()
        print(f"✅ Seeded {len(suppliers)} suppliers")
        print(f"✅ Seeded {len(customers)} customers")

        # Seed items and stock
        print("🔄 Creating items and stock...")
        items = []
        for _ in range(20):
            try:
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
            except Exception as e:
                print(f"❌ Failed to create item and stock: {e}")

        db.session.commit()
        print(f"✅ Seeded {len(items)} items and stock entries")

        # Seed purchases and payments
        print("🔄 Creating purchases and payments...")
        purchases = []
        payments = []

        for _ in range(30):
            try:
                item = random.choice(items)
                supplier = random.choice(suppliers)
                quantity = random.randint(1, 20)
                unit_price = round(random.uniform(50, 500), 2)
                total = round(quantity * unit_price, 2)
                purchase_date = datetime.now(timezone.utc)

                status = PaymentStatus.UNPAID
                payment = None

                if random.choice([True, False]):  # Should be paid
                    try:
                        method = random.choice(list(PaymentMethod))
                        bank_account = None

                        if method == PaymentMethod.BANK:
                            bank_account = random.choice(list(BankAccounts))

                        payment = Payment(
                            method=method,
                            bank_account=bank_account,
                            amount_paid=total,
                            is_paid=True,
                            payment_date=datetime.now(timezone.utc)
                        )
                        status = PaymentStatus.PAID
                        print(f"💰 Creating paid purchase with method: {method.value}" + (f" | Bank: {bank_account.value}" if bank_account else ""))
                    except Exception as e:
                        print(f"❌ Failed to prepare payment: {e}")
                        payment = None
                        status = PaymentStatus.UNPAID

                # Create purchase
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

                if payment:
                    payment.purchase_id = purchase.purchase_id
                    db.session.add(payment)
                    payments.append(payment)

                # Update stock
                stock = Stock.query.filter_by(item_id=item.item_id).first()
                if stock:
                    stock.quantity += quantity

                purchases.append(purchase)

            except Exception as e:
                print(f"❌ Error creating purchase/payment: {e}")

        db.session.commit()
        print(f"✅ Seeded {len(purchases)} purchases")
        print(f"✅ Seeded {len(payments)} payments")


                # Seed sales and payments
        print("🔄 Creating sales and payments...")
        sales = []
        sale_payments = []

        for _ in range(30):
            try:
                item = random.choice(items)
                customer = random.choice(customers)

                stock = Stock.query.filter_by(item_id=item.item_id).first()
                if not stock or stock.quantity < 1:
                    continue  # Skip sale if no stock available

                quantity = random.randint(1, min(stock.quantity, 10))
                unit_price = round(random.uniform(100, 600), 2)
                total = round(quantity * unit_price, 2)
                sale_date = datetime.now(timezone.utc)

                status = PaymentStatus.UNPAID.value
                payment = None

                if random.choice([True, False]):
                    try:
                        method = random.choice(list(PaymentMethod))
                        bank_account = None
                        if method == PaymentMethod.BANK:
                            bank_account = random.choice(list(BankAccounts))

                        payment = Payment(
                            method=method,
                            bank_account=bank_account,
                            amount_paid=total,
                            is_paid=True,
                            payment_date=sale_date
                        )
                        status = PaymentStatus.PAID.value
                        print(f"🧾 Creating paid sale with method: {method.value}" + (f" | Bank: {bank_account.value}" if bank_account else ""))
                    except Exception as e:
                        print(f"❌ Failed to prepare sale payment: {e}")
                        payment = None
                        status = PaymentStatus.UNPAID.value

                # Create the sale
                sale = Sale(
                    item_id=item.item_id,
                    customer_id=customer.customer_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_amount=total,
                    payment_status=status,
                    sale_date=sale_date
                )
                db.session.add(sale)
                db.session.flush()

                if payment:
                    payment.sale_id = sale.sale_id
                    db.session.add(payment)
                    sale_payments.append(payment)

                # Update stock
                stock.quantity -= quantity
                sales.append(sale)

            except Exception as e:
                print(f"❌ Error creating sale/payment: {e}")

        db.session.commit()
        print(f"✅ Seeded {len(sales)} sales")
        print(f"✅ Seeded {len(sale_payments)} sale payments")


        print("🎉 All data seeded successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ SEEDING FAILED: {e}")
