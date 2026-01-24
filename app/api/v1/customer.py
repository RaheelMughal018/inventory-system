from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.services.customer_service import (
    get_customer_by_id,
    get_all_customers,
    create_customer,
    update_customer,
    delete_customer
)
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all customers with optional search filtering.
    Requires authentication.
    """
    try:
        customers, total = get_all_customers(db, skip=skip, limit=limit, search=search)
        
        customer_responses = []
        for customer in customers:
            profile = customer.profile
            customer_responses.append(CustomerResponse(
                id=customer.id,
                user_id=customer.user_id,
                email=customer.email,
                name=customer.name,
                company_name=profile.company_name if profile else None,
                phone=profile.phone if profile else None,
                city=profile.city if profile else None,
                created_at=customer.created_at,
                updated_at=customer.updated_at,
                created_by_id=customer.created_by_id,
                total_transactions=profile.total_transactions if profile else None,
                total_paid=profile.total_paid if profile else None,
                current_balance=profile.current_balance if profile else None,
                profile_picture=profile.profile_picture if profile else None
            ))
        
        return CustomerListResponse(
            total=total,
            customers=customer_responses
        )
    except Exception as e:
        logger.error(f"Error fetching customers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch customers"
        )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get customer by ID.
    Requires authentication.
    """
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="customer not found"
        )
    
    profile = customer.profile
    return CustomerResponse(
        id=customer.id,
        user_id=customer.user_id,
        email=customer.email,
        name=customer.name,
        company_name=profile.company_name if profile else None,
        phone=profile.phone if profile else None,
        city=profile.city if profile else None,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        created_by_id=customer.created_by_id,
        total_transactions=profile.total_transactions if profile else None,
        total_paid=profile.total_paid if profile else None,
        current_balance=profile.current_balance if profile else None,
        profile_picture=profile.profile_picture if profile else None
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer_route(
    customer_data: CustomerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new customer.
    Requires authentication.
    The created_by_id will be set to the current user's ID.
    """
    try:
        customer = create_customer(
            db=db,
            name=customer_data.name,
            company_name=customer_data.company_name,
            phone=customer_data.phone,
            city=customer_data.city,
            created_by_id=current_user.id
        )
        
        logger.info(f"customer {customer.email} created by {current_user.email}")
        
        profile = customer.profile
        return CustomerResponse(
            id=customer.id,
            user_id=customer.user_id,
            email=None,
            name=customer.name,
            company_name=profile.company_name if profile else None,
            phone=profile.phone if profile else None,
            city=profile.city if profile else None,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            created_by_id=customer.created_by_id,
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
        logger.error(f"Error creating customer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer"
        )


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer_route(
    customer_id: int,
    customer_data: CustomerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update customer information.
    Requires authentication.
    Users can only update their own profile unless they are owners.
    """
    # Check if user is updating themselves or is an owner
    if customer_id != current_user.id and current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this customer"
        )
    
    try:
        customer = update_customer(
            db=db,
            customer_id=customer_id,
            name=customer_data.name,
            email=customer_data.email,
            company_name=customer_data.company_name,
            phone=customer_data.phone,
            city=customer_data.city
        )
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="customer not found"
            )
        
        logger.info(f"customer {customer_id} updated by {current_user.email}")
        
        profile = customer.profile
        return CustomerResponse(
            id=customer.id,
            user_id=customer.user_id,
            email=customer.email,
            name=customer.name,
            company_name=profile.company_name if profile else None,
            phone=profile.phone if profile else None,
            city=profile.city if profile else None,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            created_by_id=customer.created_by_id,
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
        logger.error(f"Error updating customer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer"
        )


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_route(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a customer.
    Requires authentication.
    Only owners can delete customers, and users cannot delete themselves.
    """
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete customers"
        )
    
    if customer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself"
        )
    
    try:
        success = delete_customer(db, customer_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="customer not found"
            )
        
        logger.info(f"customer {customer_id} deleted by {current_user.email}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting customer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete customer"
        )
