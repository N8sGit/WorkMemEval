"""Tests for product catalog endpoints."""

from decimal import Decimal


class TestProductList:
    """Test product listing."""

    def test_list_products_empty(self, client):
        """Returns empty list when no products."""
        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_products(self, client, test_product):
        """Returns products with pagination."""
        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test T-Shirt"
        assert data["total"] == 1
        assert data["page"] == 1

    def test_list_products_pagination(self, client, admin_headers, db_session):
        """Pagination works correctly."""
        # Create multiple products
        from shopmind.models import Product
        for i in range(5):
            product = Product(
                name=f"Product {i}",
                slug=f"product-{i}",
                base_price=Decimal("10.00"),
            )
            db_session.add(product)
        db_session.commit()

        # First page
        response = client.get("/api/products?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

        # Second page
        response = client.get("/api/products?page=2&page_size=2")
        data = response.json()
        assert len(data["items"]) == 2


class TestProductDetail:
    """Test single product retrieval."""

    def test_get_product_by_id(self, client, test_product):
        """Get product by ID includes variants."""
        response = client.get(f"/api/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test T-Shirt"
        assert len(data["variants"]) == 3

    def test_get_product_by_slug(self, client, test_product):
        """Get product by slug works."""
        response = client.get("/api/products/slug/test-tshirt")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id

    def test_get_product_not_found(self, client):
        """Returns 404 for nonexistent product."""
        response = client.get("/api/products/999")
        assert response.status_code == 404

    def test_variant_pricing(self, client, test_product):
        """Variant final_price includes price modifier."""
        response = client.get(f"/api/products/{test_product.id}")
        data = response.json()
        variants = {v["sku"]: v for v in data["variants"]}

        # Base price is 29.99
        assert Decimal(variants["TST-S-BLU"]["final_price"]) == Decimal("29.99")
        assert Decimal(variants["TST-M-BLU"]["final_price"]) == Decimal("34.99")  # +5
        assert Decimal(variants["TST-L-RED"]["final_price"]) == Decimal("39.99")  # +10


class TestProductCreate:
    """Test product creation (admin only)."""

    def test_create_product_admin(self, client, admin_headers):
        """Admins can create products."""
        response = client.post(
            "/api/products",
            headers=admin_headers,
            json={
                "name": "New Product",
                "slug": "new-product",
                "description": "A new product",
                "base_price": "19.99",
                "variants": [
                    {"sku": "NEW-001", "attributes": {"size": "M"}, "stock_quantity": 20}
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Product"
        assert data["has_variants"] is True
        assert len(data["variants"]) == 1

    def test_create_product_user_forbidden(self, client, auth_headers):
        """Regular users cannot create products."""
        response = client.post(
            "/api/products",
            headers=auth_headers,
            json={
                "name": "New Product",
                "slug": "new-product",
                "base_price": "19.99",
            },
        )
        assert response.status_code == 403

    def test_create_product_duplicate_slug(self, client, admin_headers, test_product):
        """Creating product with existing slug fails."""
        response = client.post(
            "/api/products",
            headers=admin_headers,
            json={
                "name": "Another Product",
                "slug": test_product.slug,
                "base_price": "19.99",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


class TestProductUpdate:
    """Test product updates (admin only)."""

    def test_update_product(self, client, admin_headers, test_product):
        """Admins can update products."""
        response = client.patch(
            f"/api/products/{test_product.id}",
            headers=admin_headers,
            json={"name": "Updated Name", "base_price": "39.99"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert Decimal(data["base_price"]) == Decimal("39.99")

    def test_update_product_not_found(self, client, admin_headers):
        """Updating nonexistent product fails."""
        response = client.patch(
            "/api/products/999",
            headers=admin_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestProductDelete:
    """Test product deletion (admin only)."""

    def test_soft_delete_product(self, client, admin_headers, test_product, db_session):
        """Default delete is soft delete."""
        response = client.delete(
            f"/api/products/{test_product.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Product still exists but is inactive
        db_session.refresh(test_product)
        assert test_product.is_active is False

        # Not visible in list
        response = client.get("/api/products")
        assert response.json()["total"] == 0

    def test_hard_delete_product(self, client, admin_headers, test_product, db_session):
        """Hard delete removes product permanently."""
        product_id = test_product.id
        response = client.delete(
            f"/api/products/{product_id}?hard_delete=true",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Product is gone
        from shopmind.models import Product
        assert db_session.query(Product).filter(Product.id == product_id).first() is None


class TestVariants:
    """Test variant management."""

    def test_create_variant(self, client, admin_headers, test_product):
        """Admins can add variants to products."""
        response = client.post(
            f"/api/products/{test_product.id}/variants",
            headers=admin_headers,
            json={
                "sku": "TST-XL-GRN",
                "attributes": {"size": "XL", "color": "green"},
                "stock_quantity": 25,
                "price_modifier": "15.00",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "TST-XL-GRN"
        assert Decimal(data["final_price"]) == Decimal("44.99")  # 29.99 + 15

    def test_create_variant_duplicate_sku(self, client, admin_headers, test_product):
        """Creating variant with existing SKU fails."""
        response = client.post(
            f"/api/products/{test_product.id}/variants",
            headers=admin_headers,
            json={"sku": "TST-S-BLU", "attributes": {}},  # Existing SKU
        )
        assert response.status_code == 400

    def test_update_variant_stock(self, client, admin_headers, test_product):
        """Admins can adjust variant stock."""
        variant = test_product.variants[0]
        initial_stock = variant.stock_quantity

        response = client.post(
            f"/api/products/variants/{variant.id}/stock?quantity_delta=5",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["stock_quantity"] == initial_stock + 5

    def test_update_variant_stock_negative(self, client, admin_headers, test_product):
        """Stock cannot go negative."""
        variant = test_product.variants[0]

        response = client.post(
            f"/api/products/variants/{variant.id}/stock?quantity_delta=-100",
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()
