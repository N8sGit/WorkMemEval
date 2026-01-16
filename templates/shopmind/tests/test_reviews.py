"""Tests for reviews and stock notifications."""

import pytest
from decimal import Decimal

from shopmind.models.reviews import Review, StockNotification
from shopmind.models.order import Order, OrderItem, OrderStatus
from shopmind.models.product import ProductVariant


# --- Fixtures ---


@pytest.fixture
def completed_order(db_session, test_user, test_variant):
    """Create a completed order for verified purchase testing."""
    order = Order(
        user_id=test_user.id,
        status=OrderStatus.DELIVERED,
        subtotal=Decimal("29.99"),
        discount_amount=Decimal("0.00"),
        total=Decimal("29.99"),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        variant_id=test_variant.id,
        quantity=1,
        unit_price=Decimal("29.99"),
        product_name=test_variant.product.name,
        variant_sku=test_variant.sku,
        variant_attributes=str(test_variant.attributes),
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def test_review(db_session, test_user, test_product):
    """Create a test review."""
    review = Review(
        user_id=test_user.id,
        product_id=test_product.id,
        rating=4,
        title="Great product!",
        body="Really enjoyed this product.",
        is_verified_purchase=False,
        is_approved=True,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


@pytest.fixture
def pending_review(db_session, test_user, test_product):
    """Create a pending (unapproved) review."""
    review = Review(
        user_id=test_user.id,
        product_id=test_product.id,
        rating=5,
        title="Amazing!",
        body="Best purchase ever.",
        is_approved=False,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


@pytest.fixture
def out_of_stock_variant(db_session, test_product):
    """Create an out-of-stock variant."""
    variant = ProductVariant(
        product_id=test_product.id,
        sku="OOS-TEST",
        attributes={"size": "XL"},
        stock_quantity=0,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(variant)
    return variant


@pytest.fixture
def stock_notification(db_session, test_user, out_of_stock_variant):
    """Create a stock notification subscription."""
    notification = StockNotification(
        user_id=test_user.id,
        variant_id=out_of_stock_variant.id,
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


# --- Review Tests ---


class TestReviews:
    """Test review endpoints."""

    def test_get_product_reviews_empty(self, client, test_product):
        """Returns empty list when no reviews."""
        response = client.get(f"/api/products/{test_product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_product_reviews(self, client, test_product, test_review):
        """Returns product reviews."""
        response = client.get(f"/api/products/{test_product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["rating"] == 4
        assert data["items"][0]["title"] == "Great product!"

    def test_get_product_reviews_excludes_unapproved(
        self, client, test_product, pending_review
    ):
        """Unapproved reviews are not shown to public."""
        response = client.get(f"/api/products/{test_product.id}/reviews")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_get_product_rating(self, client, test_product, test_review):
        """Returns rating summary for product."""
        response = client.get(f"/api/products/{test_product.id}/rating")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_rating"] == 4.0
        assert data["review_count"] == 1
        assert "rating_distribution" in data

    def test_create_review(self, client, auth_headers, test_product):
        """Can create a review."""
        response = client.post(
            "/api/reviews",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "rating": 5,
                "title": "Excellent!",
                "body": "Would buy again.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        assert data["title"] == "Excellent!"
        assert data["is_approved"] is False  # Requires moderation

    def test_create_review_verified_purchase(
        self, client, auth_headers, test_product, completed_order
    ):
        """Review from buyer is marked as verified purchase."""
        response = client.post(
            "/api/reviews",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "rating": 5,
                "title": "Verified!",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_verified_purchase"] is True

    def test_create_review_duplicate(self, client, auth_headers, test_product, test_review):
        """Cannot create duplicate review for same product."""
        response = client.post(
            "/api/reviews",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "rating": 3,
            },
        )
        assert response.status_code == 400
        assert "already reviewed" in response.json()["detail"]

    def test_create_review_invalid_product(self, client, auth_headers):
        """Returns 404 for nonexistent product."""
        response = client.post(
            "/api/reviews",
            headers=auth_headers,
            json={
                "product_id": 9999,
                "rating": 5,
            },
        )
        assert response.status_code == 404

    def test_create_review_invalid_rating(self, client, auth_headers, test_product):
        """Validates rating range 1-5."""
        response = client.post(
            "/api/reviews",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "rating": 6,
            },
        )
        assert response.status_code == 422

    def test_create_review_requires_auth(self, client, test_product):
        """Creating review requires authentication."""
        response = client.post(
            "/api/reviews",
            json={"product_id": test_product.id, "rating": 5},
        )
        assert response.status_code == 401

    def test_get_my_reviews(self, client, auth_headers, test_review):
        """Returns current user's reviews."""
        response = client.get("/api/reviews/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == test_review.id

    def test_update_review(self, client, auth_headers, test_review):
        """Can update own review."""
        response = client.patch(
            f"/api/reviews/{test_review.id}",
            headers=auth_headers,
            json={"rating": 5, "title": "Updated title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        assert data["title"] == "Updated title"
        assert data["is_approved"] is False  # Reset on edit

    def test_update_review_not_owner(self, client, admin_headers, test_review):
        """Cannot update someone else's review."""
        response = client.patch(
            f"/api/reviews/{test_review.id}",
            headers=admin_headers,
            json={"rating": 1},
        )
        assert response.status_code == 403

    def test_delete_review(self, client, auth_headers, test_review):
        """Can delete own review."""
        response = client.delete(
            f"/api/reviews/{test_review.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_delete_review_admin(self, client, admin_headers, test_review):
        """Admin can delete any review."""
        response = client.delete(
            f"/api/reviews/{test_review.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204


# --- Review Moderation Tests ---


class TestReviewModeration:
    """Test review moderation (admin)."""

    def test_get_pending_reviews(self, client, admin_headers, pending_review):
        """Admin can get pending reviews."""
        response = client.get("/api/admin/reviews/pending", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == pending_review.id

    def test_get_pending_reviews_user_forbidden(self, client, auth_headers):
        """Regular users cannot access pending reviews."""
        response = client.get("/api/admin/reviews/pending", headers=auth_headers)
        assert response.status_code == 403

    def test_approve_review(self, client, admin_headers, pending_review, db_session, test_product):
        """Admin can approve review."""
        response = client.post(
            f"/api/admin/reviews/{pending_review.id}/moderate",
            headers=admin_headers,
            json={"is_approved": True},
        )
        assert response.status_code == 200
        assert response.json()["is_approved"] is True

        # Check product rating was updated
        db_session.refresh(test_product)
        assert test_product.review_count == 1
        assert test_product.avg_rating is not None

    def test_reject_review(self, client, admin_headers, pending_review):
        """Admin can reject review."""
        response = client.post(
            f"/api/admin/reviews/{pending_review.id}/moderate",
            headers=admin_headers,
            json={"is_approved": False},
        )
        assert response.status_code == 200
        assert response.json()["is_approved"] is False


# --- Rating Aggregation Tests ---


class TestRatingAggregation:
    """Test rating aggregation on products."""

    def test_rating_updates_on_approve(
        self, client, admin_headers, db_session, test_product, pending_review
    ):
        """Product rating updates when review is approved."""
        # Approve review
        client.post(
            f"/api/admin/reviews/{pending_review.id}/moderate",
            headers=admin_headers,
            json={"is_approved": True},
        )

        db_session.refresh(test_product)
        assert test_product.review_count == 1
        assert float(test_product.avg_rating) == 5.0

    def test_rating_updates_on_delete(
        self, client, auth_headers, db_session, test_product, test_review
    ):
        """Product rating updates when review is deleted."""
        # Delete review
        client.delete(f"/api/reviews/{test_review.id}", headers=auth_headers)

        db_session.refresh(test_product)
        assert test_product.review_count == 0
        assert test_product.avg_rating is None

    def test_rating_distribution(self, client, db_session, test_product, test_user):
        """Rating distribution is calculated correctly."""
        # Create multiple reviews with different ratings
        for i, rating in enumerate([5, 5, 4, 3, 1]):
            from shopmind.models.user import User

            user = User(
                email=f"reviewer{i}@test.com",
                password_hash="hash",
                full_name=f"Reviewer {i}",
            )
            db_session.add(user)
            db_session.flush()

            review = Review(
                user_id=user.id,
                product_id=test_product.id,
                rating=rating,
                is_approved=True,
            )
            db_session.add(review)

        db_session.commit()

        response = client.get(f"/api/products/{test_product.id}/rating")
        data = response.json()
        assert data["review_count"] == 5
        assert data["rating_distribution"]["5"] == 2
        assert data["rating_distribution"]["4"] == 1
        assert data["rating_distribution"]["3"] == 1
        assert data["rating_distribution"]["1"] == 1


# --- Stock Notification Tests ---


class TestStockNotifications:
    """Test back-in-stock notification endpoints."""

    def test_subscribe_to_notification(
        self, client, auth_headers, out_of_stock_variant
    ):
        """Can subscribe to back-in-stock notification."""
        response = client.post(
            "/api/stock-notifications",
            headers=auth_headers,
            json={"variant_id": out_of_stock_variant.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["variant_id"] == out_of_stock_variant.id

    def test_subscribe_guest_with_email(self, client, out_of_stock_variant):
        """Guest can subscribe with email."""
        response = client.post(
            "/api/stock-notifications",
            json={
                "variant_id": out_of_stock_variant.id,
                "email": "guest@example.com",
            },
        )
        assert response.status_code == 201

    def test_subscribe_guest_without_email(self, client, out_of_stock_variant):
        """Guest must provide email."""
        response = client.post(
            "/api/stock-notifications",
            json={"variant_id": out_of_stock_variant.id},
        )
        assert response.status_code == 400
        assert "Email is required" in response.json()["detail"]

    def test_subscribe_in_stock_variant(self, client, auth_headers, test_variant):
        """Cannot subscribe to in-stock variant."""
        response = client.post(
            "/api/stock-notifications",
            headers=auth_headers,
            json={"variant_id": test_variant.id},
        )
        assert response.status_code == 400
        assert "already in stock" in response.json()["detail"]

    def test_subscribe_duplicate(
        self, client, auth_headers, out_of_stock_variant, stock_notification
    ):
        """Cannot subscribe twice to same variant."""
        response = client.post(
            "/api/stock-notifications",
            headers=auth_headers,
            json={"variant_id": out_of_stock_variant.id},
        )
        assert response.status_code == 400
        assert "already subscribed" in response.json()["detail"]

    def test_subscribe_nonexistent_variant(self, client, auth_headers):
        """Returns 404 for nonexistent variant."""
        response = client.post(
            "/api/stock-notifications",
            headers=auth_headers,
            json={"variant_id": 9999},
        )
        assert response.status_code == 404

    def test_get_my_notifications(
        self, client, auth_headers, stock_notification
    ):
        """Returns user's notification subscriptions."""
        response = client.get("/api/stock-notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["variant_id"] == stock_notification.variant_id

    def test_unsubscribe(
        self, client, auth_headers, out_of_stock_variant, stock_notification
    ):
        """Can unsubscribe from notification."""
        response = client.delete(
            f"/api/stock-notifications/{out_of_stock_variant.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify unsubscribed
        response = client.get("/api/stock-notifications", headers=auth_headers)
        assert response.json()["total"] == 0

    def test_check_subscription(
        self, client, auth_headers, out_of_stock_variant, stock_notification
    ):
        """Can check if subscribed to variant."""
        response = client.get(
            f"/api/stock-notifications/check/{out_of_stock_variant.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_subscribed"] is True

    def test_check_not_subscribed(self, client, auth_headers, test_variant):
        """Returns false when not subscribed."""
        response = client.get(
            f"/api/stock-notifications/check/{test_variant.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_subscribed"] is False
