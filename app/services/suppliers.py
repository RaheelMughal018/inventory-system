# app/services/supplier_service.py
import uuid
from app.models.supplier import Supplier
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app import db
from flask import current_app


def get_all_suppliers(page, limit, search=None):
    try:
        base_query = Supplier.query

        if search:
            base_query = base_query.filter(Supplier.name.ilike(f"%{search.strip()}%"))

        paginated = base_query.paginate(page=page, per_page=limit, error_out=False)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    'supplier_id': str(c.supplier_id),
                    'name': c.name,
                    'phone': c.phone,
                    'address': c.address,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                    'updated_at': c.updated_at.isoformat() if c.updated_at else None
                }
                for c in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def create_supplier(data):
    try:
        new_supplier = Supplier(
            supplier_id = str(uuid.uuid4()),
            name = data.get('name'),
            phone = data.get('phone'),
            address = data.get('address'),
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc),
        )
        db.session.add(new_supplier)
        db.session.commit()


        return {
            'supplier_id': new_supplier.supplier_id,
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
            'supplier_id': str(supplier.supplier_id),
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
            'supplier_id': str(supplier.supplier_id),
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

def get_supplier_by_id(supplier_id):
    print("getting customer by id")
    try:
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return None
        return {
            'supplier_id': str(supplier.supplier_id),
            'name': supplier.name,
            'phone': supplier.phone,
            'address': supplier.address,
            'created_at': supplier.created_at.isoformat() if supplier.created_at else None,
            'updated_at': supplier.updated_at.isoformat() if supplier.updated_at else None
        }
    
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

