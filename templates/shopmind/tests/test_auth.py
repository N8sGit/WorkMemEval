"""Tests for authentication endpoints."""

import pytest


class TestRegistration:
    """Test user registration."""

    def test_register_success(self, client):
        """Users can register with valid data."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_admin"] is False
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Registration fails for existing email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Registration fails for invalid email format."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Registration fails for password < 8 chars."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Test user login."""

    def test_login_success(self, client, test_user):
        """Users can login with correct credentials."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Login fails with wrong password."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login fails for nonexistent user."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nobody@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session, test_user):
        """Login fails for inactive user."""
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 401


class TestProtectedRoutes:
    """Test authentication middleware."""

    def test_me_authenticated(self, client, test_user, auth_headers):
        """Authenticated users can access /me."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email

    def test_me_unauthenticated(self, client):
        """Unauthenticated requests are rejected."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """Invalid tokens are rejected."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_admin_route_as_admin(self, client, admin_headers, test_product):
        """Admins can access admin routes."""
        response = client.get("/api/orders/admin/all", headers=admin_headers)
        assert response.status_code == 200

    def test_admin_route_as_user(self, client, auth_headers):
        """Regular users cannot access admin routes."""
        response = client.get("/api/orders/admin/all", headers=auth_headers)
        assert response.status_code == 403
