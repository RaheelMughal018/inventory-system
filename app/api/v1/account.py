from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from starlette.status import HTTP_201_CREATED
from app.core.dependencies import get_db, get_current_active_user
from app.models.payment import PaymentAccountType
from app.models.user import User
from app.services.account_service import (
    create_account,
    get_account_by_id,
    get_account_by_name,
    get_all_accounts,
    update_account,
    delete_account
)
from app.schemas.account import (
    AccountDeleteResponse,
    AccountResponse,
    AccountListResponse,
    AccountCreate,
    UpdateAccount,
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=AccountListResponse)
def get_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=20),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    type: Optional[PaymentAccountType] = Query(None),
    db: Session = Depends(get_db)
):
    """ Get all the Accounts """
    try:
        accounts, total = get_all_accounts(db, skip, limit, search, type)

        return AccountListResponse(
            total=total,
            accounts=[AccountResponse.model_validate(
                account) for account in accounts]
        )
    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch accounts"
        )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get Account by Id
    """
    account = get_account_by_id(db, account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not Found"
        )

    return AccountResponse.model_validate(account)


@router.post("", response_model=AccountResponse, status_code=HTTP_201_CREATED)
def create_account_route(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ 
    Create Account
    """
    try:
        account = create_account(
            db=db,
            name=account_data.name,
            type=account_data.type
        )
        logger.info(
            f"Account {account_data.name} created by {current_user.name}")

        return AccountResponse.model_validate(account)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )


@router.put("/{account_id}", response_model=AccountResponse)
def update_account_route(
    account_id: str,
    account_data: UpdateAccount,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update item information.
    Requires authentication.
    """
    try:
        account = update_account(
            db=db,
            account_id=account_id,
            name=account_data.name,
            type=account_data.type,

        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        logger.info(f"Account {account_id} updated by {current_user.name}")

        return AccountResponse.model_validate(account)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating Account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update Account"
        )


@router.delete("/{account_id}", response_model=AccountDeleteResponse)
def delete_account_route(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an item.
    Requires authentication.
    Only owners can delete items.
    """
    from app.models.user import UserRole

    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete items"
        )

    try:
        success = delete_account(db, account_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )

        logger.info(f"Item {account_id} deleted by {current_user.name}")

        return AccountDeleteResponse(
            message="Item deleted successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )
