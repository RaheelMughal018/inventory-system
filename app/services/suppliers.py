# app/services/supplier_service.py
import uuid
from app.models.supplier import Supplier
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app import db
from flask import current_app


def get_all_suppliers():
    try:
        suppliers = Supplier.query.all()
        return [
            {
                'id': str(supplier.id),
                'name': supplier.name,
                'phone': supplier.phone,
                'address': supplier.address,
                'created_at': supplier.created_at.isoformat(),
                'updated_at': supplier.updated_at.isoformat(),
            }
            for supplier in suppliers
        ]
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")


def create_supplier(data):
    try:
        new_supplier = Supplier(
            id = str(uuid.uuid4()),
            name = data.get('name'),
            phone = data.get('phone'),
            address = data.get('address'),
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc),
        )
        db.session.add(new_supplier)
        db.session.commit()


        return {
            'id': new_supplier.id,
            'name': new_supplier.name,
            'phone': new_supplier.phone,
            'address': new_supplier.address,
            'created_at': new_supplier.created_at.isoformat(),
            'updated_at': new_supplier.updated_at.isoformat()
        }
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database Error: {str(e)}")
    

def update_supplier(supplier_id, data):
    try:
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            raise ValueError("Supplier not found")

        supplier.name = data.get("name", supplier.name)
        supplier.phone = data.get("phone", supplier.phone)
        supplier.address = data.get("address", supplier.address)

        db.session.commit()
        return {
            'id': str(supplier.id),
            'name': supplier.name,
            'phone': supplier.phone,
            'address': supplier.address,
            'created_at': supplier.created_at.isoformat() if supplier.created_at else None,
            'updated_at': supplier.updated_at.isoformat() if supplier.updated_at else None
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
    
def delete_supplier(supplier_id):
    try:
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            raise ValueError("Supplier not found")

        db.session.delete(supplier)
        db.session.commit()
        return {
            'id': str(supplier.id),
            'name': supplier.name,
            'phone': supplier.phone,
            'address': supplier.address,
            
        }
    except ValueError as ve:
        current_app.logger.warning(str(ve))
        raise ve
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

