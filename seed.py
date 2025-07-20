from app import create_app, db
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.item import Item
from app.models.category import Category
from faker import Faker
import uuid
import random
from datetime import datetime, timezone

fake = Faker()
app = create_app()

with app.app_context():
    # Optional: Clear existing data
    db.session.query(Category).delete()
    db.session.query(Item).delete()
    db.session.query(Customer).delete()
    db.session.query(Supplier).delete()

    db.session.commit()

    num_suppliers = random.randint(30, 40)
    num_customers = random.randint(30, 40)
    num_items = random.randint(30, 40)

    suppliers = []
    customers = []
    items = []
    categories = []

    for _ in range(num_suppliers):
        raw_phone = fake.phone_number()
        clean_phone = ''.join(filter(str.isdigit, raw_phone))[:20]
        supplier = Supplier(
            id=str(uuid.uuid4()),
            name=fake.company(),
            phone=clean_phone,
            address=fake.address().replace('\n', ', '),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        suppliers.append(supplier)

    for _ in range(num_customers):
        raw_phone = fake.phone_number()
        clean_phone = ''.join(filter(str.isdigit, raw_phone))[:20]
        customer = Customer(
            id=str(uuid.uuid4()),
            name=fake.company(),
            phone=clean_phone,
            address=fake.address().replace('\n', ', '),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        customers.append(customer)

    for _ in range(num_items):
        item = Item(
            id=str(uuid.uuid4()),
            name=fake.word().capitalize() + " " + fake.random_element(elements=('Sensor', 'Capacitor', 'Transistor', 'LED', 'Module')),
            price=round(random.uniform(10.0, 100.0), 2),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        items.append(item)

    db.session.add_all(suppliers)
    db.session.add_all(customers)
    db.session.add_all(items)
    db.session.commit()

    # Add 1–3 categories per item
    for item in items:
        for _ in range(random.randint(1, 3)):
            category = Category(
                id=str(uuid.uuid4()),
                name=fake.word().capitalize() + " Category",
                item_id=item.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            categories.append(category)

    db.session.add_all(categories)
    db.session.commit()

    print(f"✅ Seeded {len(suppliers)} suppliers")
    print(f"✅ Seeded {len(customers)} customers")
    print(f"✅ Seeded {len(items)} items")
    print(f"✅ Seeded {len(categories)} categories")
