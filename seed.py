from app import create_app, db
from app.models.supplier import Supplier 
from app.models.customer import Customer 
from faker import Faker
import uuid
import random
from datetime import datetime, timezone

fake = Faker()
app = create_app()

with app.app_context():
    # Optional: Clear existing suppliers
    Supplier.query.delete()

    # Generate 30–40 random suppliers
    num_suppliers = random.randint(30, 40)
    num_customers = random.randint(30, 40)
    suppliers = []
    customers = []

    raw_phone = fake.phone_number()
    clean_phone = ''.join(filter(str.isdigit, raw_phone))[:20]


    for _ in range(num_suppliers):
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
        customer = Customer(
            id=str(uuid.uuid4()),
            name=fake.company(),
            phone=clean_phone,
            address=fake.address().replace('\n', ', '),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        customers.append(customer)

    db.session.add_all(suppliers)
    db.session.add_all(customers)
    db.session.commit()

    print(f"✅ Seeded {num_suppliers} random suppliers successfully.")
    print(f"✅ Seeded {num_customers} random customers successfully.")
