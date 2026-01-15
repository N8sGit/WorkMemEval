"""
Service for reviews and stock notifications.

Handles review CRUD, rating aggregation, and back-in-stock subscriptions.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from shopmind.models.reviews import Review, StockNotification
from shopmind.models.product import Product, ProductVariant
from shopmind.models.order import Order, OrderItem
from shopmind.models.user import User
from shopmind.schemas.reviews import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    StockNotificationCreate,
    StockNotificationResponse,
    ProductRatingSummary,
)


# --- Review Operations ---


def get_review(db: Session, review_id: int) -> Review | None:
    """Get a review by ID."""
    return db.query(Review).filter(Review.id == review_id).first()


def get_user_review_for_product(
    db: Session, user: User, product_id: int
) -> Review | None:
    """Get a user's review for a specific product."""
    return (
        db.query(Review)
        .filter(Review.user_id == user.id, Review.product_id == product_id)
        .first()
    )


def get_product_reviews(
    db: Session,
    product_id: int,
    page: int = 1,
    page_size: int = 10,
    approved_only: bool = True,
) -> tuple[list[Review], int]:
    """Get reviews for a product with pagination."""
    query = db.query(Review).filter(Review.product_id == product_id)

    if approved_only:
        query = query.filter(Review.is_approved == True)

    total = query.count()
    skip = (page - 1) * page_size

    reviews = (
        query.options(joinedload(Review.user))
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    return reviews, total


def get_user_reviews(
    db: Session, user: User, page: int = 1, page_size: int = 10
) -> tuple[list[Review], int]:
    """Get all reviews by a user."""
    query = db.query(Review).filter(Review.user_id == user.id)

    total = query.count()
    skip = (page - 1) * page_size

    reviews = (
        query.options(joinedload(Review.product))
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    return reviews, total


def create_review(db: Session, user: User, review_data: ReviewCreate) -> Review:
    """Create a new review."""
    # Check product exists
    product = db.query(Product).filter(Product.id == review_data.product_id).first()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check if user already reviewed this product
    existing = get_user_review_for_product(db, user, review_data.product_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product",
        )

    # Check if verified purchase
    is_verified = _check_verified_purchase(db, user.id, review_data.product_id)
    order_id = _get_order_for_review(db, user.id, review_data.product_id)

    review = Review(
        user_id=user.id,
        product_id=review_data.product_id,
        order_id=order_id,
        rating=review_data.rating,
        title=review_data.title,
        body=review_data.body,
        is_verified_purchase=is_verified,
        is_approved=False,  # Requires moderation
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return review


def update_review(db: Session, review: Review, update_data: ReviewUpdate) -> Review:
    """Update an existing review."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(review, field, value)

    # Reset approval on edit
    review.is_approved = False

    db.commit()
    db.refresh(review)

    # Recalculate ratings if this review was previously approved
    update_product_rating_aggregates(db, review.product_id)

    return review


def delete_review(db: Session, review: Review) -> None:
    """Delete a review."""
    product_id = review.product_id
    db.delete(review)
    db.commit()

    # Recalculate ratings
    update_product_rating_aggregates(db, product_id)


def moderate_review(db: Session, review: Review, is_approved: bool) -> Review:
    """Approve or reject a review (admin action)."""
    review.is_approved = is_approved
    db.commit()
    db.refresh(review)

    # Recalculate product ratings
    update_product_rating_aggregates(db, review.product_id)

    return review


def get_pending_reviews(
    db: Session, page: int = 1, page_size: int = 20
) -> tuple[list[Review], int]:
    """Get reviews pending moderation (admin)."""
    query = db.query(Review).filter(Review.is_approved == False)

    total = query.count()
    skip = (page - 1) * page_size

    reviews = (
        query.options(joinedload(Review.user), joinedload(Review.product))
        .order_by(Review.created_at.asc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    return reviews, total


# --- Rating Aggregation ---


def update_product_rating_aggregates(db: Session, product_id: int) -> None:
    """Recalculate and update product rating aggregates."""
    result = (
        db.query(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .filter(Review.product_id == product_id, Review.is_approved == True)
        .first()
    )

    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        if result and result.review_count > 0:
            # Round to 1 decimal place
            product.avg_rating = round(Decimal(str(result.avg_rating)), 1)
            product.review_count = result.review_count
        else:
            product.avg_rating = None
            product.review_count = 0

        db.commit()


def get_product_rating_summary(db: Session, product_id: int) -> ProductRatingSummary:
    """Get rating summary for a product."""
    # Get avg and count
    stats = (
        db.query(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .filter(Review.product_id == product_id, Review.is_approved == True)
        .first()
    )

    # Get distribution
    distribution_result = (
        db.query(Review.rating, func.count(Review.id).label("count"))
        .filter(Review.product_id == product_id, Review.is_approved == True)
        .group_by(Review.rating)
        .all()
    )

    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for row in distribution_result:
        distribution[str(row.rating)] = row.count

    avg_rating = float(stats.avg_rating) if stats and stats.avg_rating else None
    review_count = stats.review_count if stats else 0

    return ProductRatingSummary(
        avg_rating=avg_rating,
        review_count=review_count,
        rating_distribution=distribution,
    )


def get_rating_distribution(db: Session, product_id: int) -> dict[str, int]:
    """Get rating distribution for a product."""
    result = (
        db.query(Review.rating, func.count(Review.id).label("count"))
        .filter(Review.product_id == product_id, Review.is_approved == True)
        .group_by(Review.rating)
        .all()
    )

    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for row in result:
        distribution[str(row.rating)] = row.count

    return distribution


# --- Helper Functions ---


def _check_verified_purchase(db: Session, user_id: int, product_id: int) -> bool:
    """Check if user has purchased this product."""
    # Look for delivered/shipped orders containing this product
    order_with_product = (
        db.query(Order)
        .join(OrderItem)
        .join(ProductVariant)
        .filter(
            Order.user_id == user_id,
            ProductVariant.product_id == product_id,
            Order.status.in_(["delivered", "shipped", "confirmed"]),
        )
        .first()
    )
    return order_with_product is not None


def _get_order_for_review(db: Session, user_id: int, product_id: int) -> int | None:
    """Get the most recent order containing this product."""
    order = (
        db.query(Order)
        .join(OrderItem)
        .join(ProductVariant)
        .filter(
            Order.user_id == user_id,
            ProductVariant.product_id == product_id,
            Order.status.in_(["delivered", "shipped", "confirmed"]),
        )
        .order_by(Order.created_at.desc())
        .first()
    )
    return order.id if order else None


def build_review_response(review: Review) -> ReviewResponse:
    """Build review response with user name."""
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        product_id=review.product_id,
        order_id=review.order_id,
        rating=review.rating,
        title=review.title,
        body=review.body,
        is_verified_purchase=review.is_verified_purchase,
        is_approved=review.is_approved,
        created_at=review.created_at,
        updated_at=review.updated_at,
        user_name=review.user.full_name if review.user else None,
    )


# --- Stock Notification Operations ---


def get_stock_notification(
    db: Session, notification_id: int
) -> StockNotification | None:
    """Get a stock notification by ID."""
    return (
        db.query(StockNotification)
        .filter(StockNotification.id == notification_id)
        .first()
    )


def get_user_stock_notifications(
    db: Session, user: User
) -> list[StockNotification]:
    """Get all stock notification subscriptions for a user."""
    return (
        db.query(StockNotification)
        .options(joinedload(StockNotification.variant).joinedload(ProductVariant.product))
        .filter(StockNotification.user_id == user.id, StockNotification.notified_at.is_(None))
        .order_by(StockNotification.created_at.desc())
        .all()
    )


def subscribe_to_stock_notification(
    db: Session, user: User | None, notification_data: StockNotificationCreate
) -> StockNotification:
    """Subscribe to back-in-stock notification."""
    # Check variant exists
    variant = (
        db.query(ProductVariant)
        .options(joinedload(ProductVariant.product))
        .filter(ProductVariant.id == notification_data.variant_id)
        .first()
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    # Check if already in stock
    if variant.stock_quantity > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This item is already in stock",
        )

    # Require email for guest users
    if not user and not notification_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for guest users",
        )

    # Check for existing subscription
    if user:
        existing = (
            db.query(StockNotification)
            .filter(
                StockNotification.user_id == user.id,
                StockNotification.variant_id == notification_data.variant_id,
                StockNotification.notified_at.is_(None),
            )
            .first()
        )
    else:
        existing = (
            db.query(StockNotification)
            .filter(
                StockNotification.email == notification_data.email,
                StockNotification.variant_id == notification_data.variant_id,
                StockNotification.notified_at.is_(None),
            )
            .first()
        )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already subscribed to notifications for this item",
        )

    notification = StockNotification(
        user_id=user.id if user else None,
        email=notification_data.email if not user else None,
        variant_id=notification_data.variant_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def unsubscribe_from_stock_notification(
    db: Session, user: User, variant_id: int
) -> None:
    """Unsubscribe from back-in-stock notification."""
    notification = (
        db.query(StockNotification)
        .filter(
            StockNotification.user_id == user.id,
            StockNotification.variant_id == variant_id,
            StockNotification.notified_at.is_(None),
        )
        .first()
    )

    if notification:
        db.delete(notification)
        db.commit()


def check_stock_notification_subscribed(
    db: Session, user: User, variant_id: int
) -> bool:
    """Check if user is subscribed to stock notifications for a variant."""
    notification = (
        db.query(StockNotification)
        .filter(
            StockNotification.user_id == user.id,
            StockNotification.variant_id == variant_id,
            StockNotification.notified_at.is_(None),
        )
        .first()
    )
    return notification is not None


def get_pending_notifications_for_variant(
    db: Session, variant_id: int
) -> list[StockNotification]:
    """Get all pending notifications for a variant (for sending when back in stock)."""
    return (
        db.query(StockNotification)
        .filter(
            StockNotification.variant_id == variant_id,
            StockNotification.notified_at.is_(None),
        )
        .all()
    )


def build_stock_notification_response(
    notification: StockNotification,
) -> StockNotificationResponse:
    """Build stock notification response with variant info."""
    variant = notification.variant
    product = variant.product if variant else None

    return StockNotificationResponse(
        id=notification.id,
        variant_id=notification.variant_id,
        email=notification.email,
        created_at=notification.created_at,
        notified_at=notification.notified_at,
        variant_sku=variant.sku if variant else None,
        product_name=product.name if product else None,
    )
