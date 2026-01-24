from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.services.supplier_service import (
    get_supplier_by_id,
    get_all_suppliers,
    create_supplier,
    update_supplier,
    delete_supplier
)
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=SupplierListResponse)
def get_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all suppliers with optional search filtering.
    Requires authentication.
    """
    try:
        suppliers, total = get_all_suppliers(db, skip=skip, limit=limit, search=search)
        
        supplier_responses = []
        for supplier in suppliers:
            profile = supplier.profile
            supplier_responses.append(SupplierResponse(
                id=supplier.id,
                user_id=supplier.user_id,
                email=supplier.email,
                name=supplier.name,
                company_name=profile.company_name if profile else None,
                phone=profile.phone if profile else None,
                city=profile.city if profile else None,
                created_at=supplier.created_at,
                updated_at=supplier.updated_at,
                created_by_id=supplier.created_by_id,
                total_transactions=profile.total_transactions if profile else None,
                total_paid=profile.total_paid if profile else None,
                current_balance=profile.current_balance if profile else None,
                profile_picture=profile.profile_picture if profile else None
            ))
        
        return SupplierListResponse(
            total=total,
            suppliers=supplier_responses
        )
    except Exception as e:
        logger.error(f"Error fetching suppliers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch suppliers"
        )


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get supplier by ID.
    Requires authentication.
    """
    supplier = get_supplier_by_id(db, supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    profile = supplier.profile
    return SupplierResponse(
        id=supplier.id,
        user_id=supplier.user_id,
        email=supplier.email,
        name=supplier.name,
        company_name=profile.company_name if profile else None,
        phone=profile.phone if profile else None,
        city=profile.city if profile else None,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
        created_by_id=supplier.created_by_id,
        total_transactions=profile.total_transactions if profile else None,
        total_paid=profile.total_paid if profile else None,
        current_balance=profile.current_balance if profile else None,
        profile_picture=profile.profile_picture if profile else None
    )


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_route(
    supplier_data: SupplierCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new supplier.
    Requires authentication.
    The created_by_id will be set to the current user's ID.
    """
    try:
        supplier = create_supplier(
            db=db,
            name=supplier_data.name,
            company_name=supplier_data.company_name,
            phone=supplier_data.phone,
            city=supplier_data.city,
            created_by_id=current_user.id
        )
        
        logger.info(f"Supplier {supplier.email} created by {current_user.email}")
        
        profile = supplier.profile
        return SupplierResponse(
            id=supplier.id,
            user_id=supplier.user_id,
            email=None,
            name=supplier.name,
            company_name=profile.company_name if profile else None,
            phone=profile.phone if profile else None,
            city=profile.city if profile else None,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
            created_by_id=supplier.created_by_id,
            total_transactions=profile.total_transactions if profile else None,
            total_paid=profile.total_paid if profile else None,
            current_balance=profile.current_balance if profile else None,
            profile_picture=profile.profile_picture if profile else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating supplier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create supplier"
        )


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier_route(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update supplier information.
    Requires authentication.
    Users can only update their own profile unless they are owners.
    """
    # Check if user is updating themselves or is an owner
    if supplier_id != current_user.id and current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this supplier"
        )
    
    try:
        supplier = update_supplier(
            db=db,
            supplier_id=supplier_id,
            name=supplier_data.name,
            email=supplier_data.email,
            company_name=supplier_data.company_name,
            phone=supplier_data.phone,
            city=supplier_data.city
        )
        
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        
        logger.info(f"Supplier {supplier_id} updated by {current_user.email}")
        
        profile = supplier.profile
        return SupplierResponse(
            id=supplier.id,
            user_id=supplier.user_id,
            email=supplier.email,
            name=supplier.name,
            company_name=profile.company_name if profile else None,
            phone=profile.phone if profile else None,
            city=profile.city if profile else None,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
            created_by_id=supplier.created_by_id,
            total_transactions=profile.total_transactions if profile else None,
            total_paid=profile.total_paid if profile else None,
            current_balance=profile.current_balance if profile else None,
            profile_picture=profile.profile_picture if profile else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating supplier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update supplier"
        )


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_route(
    supplier_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a supplier.
    Requires authentication.
    Only owners can delete suppliers, and users cannot delete themselves.
    """
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete suppliers"
        )
    
    if supplier_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself"
        )
    
    try:
        success = delete_supplier(db, supplier_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        
        logger.info(f"Supplier {supplier_id} deleted by {current_user.email}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting supplier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete supplier"
        )
