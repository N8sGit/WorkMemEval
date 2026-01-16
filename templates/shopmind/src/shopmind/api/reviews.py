"""
Review and stock notification API endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.schemas.reviews import (
    ReviewCreate,
    ReviewUpdate,
    ReviewModerate,
    ReviewResponse,
    ReviewListResponse,
    ProductRatingSummary,
    StockNotificationCreate,
    StockNotificationResponse,
    StockNotificationList,
)
from shopmind.services.auth import get_current_user, get_current_user_optional, get_current_admin
from shopmind.services import reviews as review_service

router = APIRouter(tags=["Reviews"])


# --- Review Endpoints ---


@router.get("/products/{product_id}/reviews", response_model=ReviewListResponse)
def get_product_reviews(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> ReviewListResponse:
    """Get reviews for a product."""
    reviews, total = review_service.get_product_reviews(
        db, product_id, page=page, page_size=page_size
    )

    pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Get rating summary
    summary = review_service.get_product_rating_summary(db, product_id)

    return ReviewListResponse(
        items=[review_service.build_review_response(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        avg_rating=summary.avg_rating,
        rating_distribution=summary.rating_distribution,
    )


@router.get("/products/{product_id}/rating", response_model=ProductRatingSummary)
def get_product_rating(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ProductRatingSummary:
    """Get rating summary for a product."""
    return review_service.get_product_rating_summary(db, product_id)


@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_data: ReviewCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReviewResponse:
    """
    Create a review for a product.

    Reviews require moderation before being displayed publicly.
    Users can only submit one review per product.
    """
    review = review_service.create_review(db, user, review_data)
    return review_service.build_review_response(review)


@router.get("/reviews/me", response_model=ReviewListResponse)
def get_my_reviews(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> ReviewListResponse:
    """Get current user's reviews."""
    reviews, total = review_service.get_user_reviews(db, user, page=page, page_size=page_size)

    pages = (total + page_size - 1) // page_size if total > 0 else 0

    return ReviewListResponse(
        items=[review_service.build_review_response(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """Get a specific review."""
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )
    return review_service.build_review_response(review)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    update_data: ReviewUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReviewResponse:
    """
    Update your review.

    Editing a review resets its approval status.
    """
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Only owner can edit
    if review.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own reviews",
        )

    review = review_service.update_review(db, review, update_data)
    return review_service.build_review_response(review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete your review."""
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Only owner or admin can delete
    if review.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )

    review_service.delete_review(db, review)


# --- Admin Review Moderation ---


@router.get("/admin/reviews/pending", response_model=ReviewListResponse)
def get_pending_reviews(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ReviewListResponse:
    """Get reviews pending moderation. **Admin only.**"""
    reviews, total = review_service.get_pending_reviews(db, page=page, page_size=page_size)

    pages = (total + page_size - 1) // page_size if total > 0 else 0

    return ReviewListResponse(
        items=[review_service.build_review_response(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/admin/reviews/{review_id}/moderate", response_model=ReviewResponse)
def moderate_review(
    review_id: int,
    moderate_data: ReviewModerate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ReviewResponse:
    """Approve or reject a review. **Admin only.**"""
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    review = review_service.moderate_review(db, review, moderate_data.is_approved)
    return review_service.build_review_response(review)


# --- Stock Notification Endpoints ---


@router.post("/stock-notifications", response_model=StockNotificationResponse, status_code=status.HTTP_201_CREATED)
def subscribe_stock_notification(
    notification_data: StockNotificationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> StockNotificationResponse:
    """
    Subscribe to back-in-stock notification.

    Authenticated users don't need to provide email.
    Guest users must provide an email address.
    """
    notification = review_service.subscribe_to_stock_notification(db, user, notification_data)
    return review_service.build_stock_notification_response(notification)


@router.get("/stock-notifications", response_model=StockNotificationList)
def get_my_stock_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> StockNotificationList:
    """Get your active stock notification subscriptions."""
    notifications = review_service.get_user_stock_notifications(db, user)
    return StockNotificationList(
        items=[review_service.build_stock_notification_response(n) for n in notifications],
        total=len(notifications),
    )


@router.delete("/stock-notifications/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_stock_notification(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Unsubscribe from back-in-stock notification for a variant."""
    review_service.unsubscribe_from_stock_notification(db, user, variant_id)


@router.get("/stock-notifications/check/{variant_id}")
def check_stock_notification(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Check if you're subscribed to stock notifications for a variant."""
    is_subscribed = review_service.check_stock_notification_subscribed(db, user, variant_id)
    return {"is_subscribed": is_subscribed}
