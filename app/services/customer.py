# app/services/customer_service.py
import uuid
from app.models.customer import Customer
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app import db
from flask import current_app


def get_all_customers():
    try:
        customers = Customer.query.all()
        return [
            {
                'id': str(customer.id),
                'name': customer.name,
                'phone': customer.phone,
                'address': customer.address,
                'created_at': customer.created_at.isoformat(),
                'updated_at': customer.updated_at.isoformat(),
            }
            for customer in customers
        ]
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")


def create_customer(data):
    try:
        new_customer = Customer(
            id = str(uuid.uuid4()),
            name = data.get('name'),
            phone = data.get('phone'),
            address = data.get('address'),
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc),
        )
        db.session.add(new_customer)
        db.session.commit()


        return {
            'id': new_customer.id,
            'name': new_customer.name,
            'phone': new_customer.phone,
            'address': new_customer.address,
            'created_at': new_customer.created_at.isoformat(),
            'updated_at': new_customer.updated_at.isoformat()
        }
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database Error: {str(e)}")
    

def update_customer(customer_id, data):
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError("customer not found")

        customer.name = data.get("name", customer.name)
        customer.phone = data.get("phone", customer.phone)
        customer.address = data.get("address", customer.address)

        db.session.commit()
        return {
            'id': str(customer.id),
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'updated_at': customer.updated_at.isoformat() if customer.updated_at else None
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
    
def delete_customer(customer_id):
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError("customer not found")

        db.session.delete(customer)
        db.session.commit()
        return {
            'id': str(customer.id),
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address,
            
        }
    except ValueError as ve:
        current_app.logger.warning(str(ve))
        raise ve
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def get_customer_by_id(customer_id):
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        return {
            'id': str(customer.id),
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'updated_at': customer.updated_at.isoformat() if customer.updated_at else None
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

