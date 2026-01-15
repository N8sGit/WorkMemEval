"""
Returns API endpoints.

Handles return requests, approvals, and refund processing.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.returns import ReturnStatus
from shopmind.schemas.returns import (
    ReturnRequest,
    ReturnApproval,
    ReturnRejection,
    ReturnReceived,
    ReturnRefund,
    ReturnResponse,
    ReturnListResponse,
    PaginatedReturns,
)
from shopmind.services.auth import get_current_user, get_current_admin
from shopmind.services import returns as return_service

router = APIRouter(prefix="/returns", tags=["Returns"])


# --- Customer Endpoints ---


@router.post("", response_model=ReturnResponse, status_code=201)
def create_return_request(
    request_data: ReturnRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReturnResponse:
    """
    Request a return for an order item.

    The order must be in delivered status.
    """
    return_request = return_service.create_return_request(db, request_data, user)
    return ReturnResponse.model_validate(return_request)


@router.get("", response_model=PaginatedReturns)
def list_my_returns(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedReturns:
    """Get current user's return requests."""
    skip = (page - 1) * page_size
    returns, total = return_service.get_user_returns(db, user, skip=skip, limit=page_size)

    return PaginatedReturns(
        items=[ReturnListResponse.model_validate(r) for r in returns],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{return_id}", response_model=ReturnResponse)
def get_return(
    return_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReturnResponse:
    """Get return details. Users can only view their own returns."""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    # Non-admins can only view their own returns
    if return_request.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return ReturnResponse.model_validate(return_request)


@router.post("/{return_id}/cancel", response_model=ReturnResponse)
def cancel_return(
    return_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReturnResponse:
    """Cancel a return request. Only the owner can cancel."""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    if return_request.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    cancelled = return_service.cancel_return(db, return_request)
    return ReturnResponse.model_validate(cancelled)


# --- Admin Endpoints ---


@router.get("/admin/all", response_model=PaginatedReturns)
def list_all_returns(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    status_filter: ReturnStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedReturns:
    """List all return requests. **Admin only.**"""
    skip = (page - 1) * page_size
    returns, total = return_service.get_all_returns(
        db,
        status_filter=status_filter,
        skip=skip,
        limit=page_size,
    )

    return PaginatedReturns(
        items=[ReturnListResponse.model_validate(r) for r in returns],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/admin/{return_id}/approve", response_model=ReturnResponse)
def approve_return(
    return_id: int,
    approval_data: ReturnApproval,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ReturnResponse:
    """Approve a return request. **Admin only.**"""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    approved = return_service.approve_return(db, return_request, approval_data)
    return ReturnResponse.model_validate(approved)


@router.post("/admin/{return_id}/reject", response_model=ReturnResponse)
def reject_return(
    return_id: int,
    rejection_data: ReturnRejection,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ReturnResponse:
    """Reject a return request. **Admin only.**"""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    rejected = return_service.reject_return(db, return_request, rejection_data)
    return ReturnResponse.model_validate(rejected)


@router.post("/admin/{return_id}/received", response_model=ReturnResponse)
def mark_return_received(
    return_id: int,
    received_data: ReturnReceived,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ReturnResponse:
    """Mark a return as received at warehouse. **Admin only.**"""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    received = return_service.mark_return_received(db, return_request, received_data)
    return ReturnResponse.model_validate(received)


@router.post("/admin/{return_id}/refund", response_model=ReturnResponse)
def process_refund(
    return_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    refund_data: ReturnRefund | None = None,
) -> ReturnResponse:
    """Process refund for a return. **Admin only.**"""
    return_request = return_service.get_return(db, return_id)

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    refunded = return_service.process_refund(db, return_request, refund_data)
    return ReturnResponse.model_validate(refunded)
