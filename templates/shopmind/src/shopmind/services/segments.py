"""
Customer segment service.

Handles segment CRUD, user assignment, and discount calculations.
"""

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from shopmind.models.segments import CustomerSegment
from shopmind.models.user import User
from shopmind.schemas.segments import (
    SegmentCreate,
    SegmentUpdate,
    SegmentResponse,
    SegmentDiscountPreview,
)


# --- Segment CRUD ---


def get_segment(db: Session, segment_id: int) -> CustomerSegment | None:
    """Get a segment by ID."""
    return db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()


def get_segment_by_slug(db: Session, slug: str) -> CustomerSegment | None:
    """Get a segment by slug."""
    return db.query(CustomerSegment).filter(CustomerSegment.slug == slug).first()


def list_segments(
    db: Session, active_only: bool = False
) -> list[CustomerSegment]:
    """List all customer segments."""
    query = db.query(CustomerSegment)

    if active_only:
        query = query.filter(CustomerSegment.is_active == True)

    return query.order_by(CustomerSegment.priority.desc(), CustomerSegment.name).all()


def create_segment(db: Session, segment_data: SegmentCreate) -> CustomerSegment:
    """Create a new customer segment."""
    segment = CustomerSegment(**segment_data.model_dump())
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


def update_segment(
    db: Session, segment: CustomerSegment, update_data: SegmentUpdate
) -> CustomerSegment:
    """Update a customer segment."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(segment, field, value)

    db.commit()
    db.refresh(segment)
    return segment


def delete_segment(db: Session, segment: CustomerSegment) -> None:
    """Delete a customer segment."""
    # Users in this segment will have segment_id set to NULL (ondelete="SET NULL")
    db.delete(segment)
    db.commit()


def get_segment_user_count(db: Session, segment_id: int) -> int:
    """Get the number of users in a segment."""
    return db.query(User).filter(User.segment_id == segment_id).count()


def get_segment_with_user_count(db: Session, segment: CustomerSegment) -> SegmentResponse:
    """Get segment response with user count."""
    user_count = get_segment_user_count(db, segment.id)
    return SegmentResponse(
        id=segment.id,
        name=segment.name,
        slug=segment.slug,
        description=segment.description,
        discount_percentage=segment.discount_percentage,
        priority=segment.priority,
        min_order_amount=segment.min_order_amount,
        max_discount_amount=segment.max_discount_amount,
        is_active=segment.is_active,
        user_count=user_count,
        created_at=segment.created_at,
        updated_at=segment.updated_at,
    )


# --- User Segment Assignment ---


def assign_user_to_segment(
    db: Session, user: User, segment_id: int | None
) -> User:
    """Assign a user to a segment (or remove from segment if None)."""
    if segment_id is not None:
        segment = get_segment(db, segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

    user.segment_id = segment_id
    db.commit()
    db.refresh(user)
    return user


def bulk_assign_segment(
    db: Session, user_ids: list[int], segment_id: int | None
) -> int:
    """
    Assign multiple users to a segment.

    Returns the number of users updated.
    """
    if segment_id is not None:
        segment = get_segment(db, segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

    updated = (
        db.query(User)
        .filter(User.id.in_(user_ids))
        .update({User.segment_id: segment_id}, synchronize_session=False)
    )
    db.commit()
    return updated


def get_users_in_segment(
    db: Session, segment_id: int, skip: int = 0, limit: int = 20
) -> tuple[list[User], int]:
    """Get paginated users in a segment."""
    query = db.query(User).filter(User.segment_id == segment_id)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total


# --- Discount Calculation ---


def calculate_segment_discount(
    db: Session, user: User | None, subtotal: Decimal
) -> tuple[Decimal, CustomerSegment | None]:
    """
    Calculate segment discount for a user.

    Args:
        db: Database session
        user: User (or None for guest)
        subtotal: Order subtotal

    Returns:
        Tuple of (discount_amount, segment)
    """
    if not user or not user.segment_id:
        return Decimal("0.00"), None

    # Get user's segment
    segment = (
        db.query(CustomerSegment)
        .filter(
            CustomerSegment.id == user.segment_id,
            CustomerSegment.is_active == True,
        )
        .first()
    )

    if not segment:
        return Decimal("0.00"), None

    discount = segment.calculate_discount(subtotal)
    return discount, segment


def preview_segment_discount(
    db: Session, user: User | None, subtotal: Decimal
) -> SegmentDiscountPreview:
    """
    Preview what segment discount would be applied.

    Useful for showing discount in cart before checkout.
    """
    discount_amount, segment = calculate_segment_discount(db, user, subtotal)

    return SegmentDiscountPreview(
        segment_name=segment.name if segment else None,
        subtotal=subtotal,
        discount_amount=discount_amount,
        discount_percentage=segment.discount_percentage if segment else Decimal("0"),
        final_subtotal=subtotal - discount_amount,
    )
