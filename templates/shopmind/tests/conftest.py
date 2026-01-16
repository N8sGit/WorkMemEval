"""
Pytest fixtures for ShopMind tests.

Provides:
- Test database with automatic cleanup
- FastAPI test client
- Helper functions for creating test data
"""

import sys
from pathlib import Path

# Add src to python path to ensure shopmind package is found
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shopmind.main import app
from shopmind.database import get_db
from shopmind.models import Base, User, Product, ProductVariant
from shopmind.services.auth import hash_password


# --- Database Fixtures ---

@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- User Fixtures ---

@pytest.fixture
def test_user(db_session) -> User:
    """Create a regular test user."""
    user = User(
        email="testuser@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        password_hash=hash_password("adminpass123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_token(client, test_user) -> str:
    """Get auth token for regular user."""
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user) -> str:
    """Get auth token for admin user."""
    response = client.post(
        "/api/auth/login",
        data={"username": admin_user.email, "password": "adminpass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token) -> dict:
    """Authorization headers for regular user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


# --- Product Fixtures ---

@pytest.fixture
def test_product(db_session) -> Product:
    """Create a test product with variants."""
    product = Product(
        name="Test T-Shirt",
        slug="test-tshirt",
        description="A test product",
        base_price=Decimal("29.99"),
        has_variants=True,
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()

    # Add variants
    variants = [
        ProductVariant(
            product_id=product.id,
            sku="TST-S-BLU",
            attributes={"size": "S", "color": "blue"},
            price_modifier=Decimal("0.00"),
            stock_quantity=10,
            low_stock_threshold=5,
        ),
        ProductVariant(
            product_id=product.id,
            sku="TST-M-BLU",
            attributes={"size": "M", "color": "blue"},
            price_modifier=Decimal("5.00"),
            stock_quantity=15,
            low_stock_threshold=5,
        ),
        ProductVariant(
            product_id=product.id,
            sku="TST-L-RED",
            attributes={"size": "L", "color": "red"},
            price_modifier=Decimal("10.00"),
            stock_quantity=0,  # Out of stock
            low_stock_threshold=5,
        ),
    ]
    for variant in variants:
        db_session.add(variant)

    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def test_variant(test_product) -> ProductVariant:
    """Get the first (in-stock) variant from test product."""
    return test_product.variants[0]
