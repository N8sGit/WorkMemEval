"""Tests for catalog organization: Categories, Tags, Collections."""

import pytest
from shopmind.models.catalog import Category, Tag, Collection


# --- Fixtures ---

@pytest.fixture
def test_category(db_session) -> Category:
    """Create a test category."""
    category = Category(
        name="Electronics",
        slug="electronics",
        description="Electronic devices",
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_subcategory(db_session, test_category) -> Category:
    """Create a subcategory."""
    subcategory = Category(
        name="Phones",
        slug="phones",
        parent_id=test_category.id,
    )
    db_session.add(subcategory)
    db_session.commit()
    db_session.refresh(subcategory)
    return subcategory


@pytest.fixture
def test_tag(db_session) -> Tag:
    """Create a test tag."""
    tag = Tag(
        name="New Arrival",
        slug="new-arrival",
        tag_type="badge",
    )
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


@pytest.fixture
def test_collection(db_session) -> Collection:
    """Create a test collection."""
    collection = Collection(
        name="Summer Sale",
        slug="summer-sale",
        description="Hot summer deals",
    )
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)
    return collection


# --- Category Tests ---

class TestCategories:
    """Test category endpoints."""

    def test_list_categories_empty(self, client):
        """Returns empty list when no categories."""
        response = client.get("/api/categories")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_categories(self, client, test_category):
        """Returns category tree."""
        response = client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Electronics"

    def test_list_categories_with_children(self, client, test_category, test_subcategory):
        """Returns categories with nested children."""
        response = client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert len(data[0]["children"]) == 1
        assert data[0]["children"][0]["name"] == "Phones"

    def test_get_category(self, client, test_category):
        """Get single category with products."""
        response = client.get(f"/api/categories/{test_category.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Electronics"
        assert "products" in data
        assert data["full_path"] == "Electronics"

    def test_get_category_not_found(self, client):
        """Returns 404 for nonexistent category."""
        response = client.get("/api/categories/999")
        assert response.status_code == 404

    def test_create_category_admin(self, client, admin_headers):
        """Admins can create categories."""
        response = client.post(
            "/api/categories",
            headers=admin_headers,
            json={
                "name": "Clothing",
                "slug": "clothing",
                "description": "Apparel and accessories",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Clothing"
        assert data["slug"] == "clothing"

    def test_create_category_with_parent(self, client, admin_headers, test_category):
        """Can create category with parent."""
        response = client.post(
            "/api/categories",
            headers=admin_headers,
            json={
                "name": "Smartphones",
                "slug": "smartphones",
                "parent_id": test_category.id,
            },
        )
        assert response.status_code == 201
        assert response.json()["parent_id"] == test_category.id

    def test_create_category_user_forbidden(self, client, auth_headers):
        """Regular users cannot create categories."""
        response = client.post(
            "/api/categories",
            headers=auth_headers,
            json={"name": "Test", "slug": "test"},
        )
        assert response.status_code == 403

    def test_create_category_duplicate_slug(self, client, admin_headers, test_category):
        """Cannot create category with existing slug."""
        response = client.post(
            "/api/categories",
            headers=admin_headers,
            json={"name": "Another", "slug": test_category.slug},
        )
        assert response.status_code == 400

    def test_update_category(self, client, admin_headers, test_category):
        """Admins can update categories."""
        response = client.patch(
            f"/api/categories/{test_category.id}",
            headers=admin_headers,
            json={"name": "Updated Electronics", "sort_order": 10},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Electronics"
        assert response.json()["sort_order"] == 10

    def test_delete_category(self, client, admin_headers, test_category):
        """Admins can delete categories."""
        response = client.delete(
            f"/api/categories/{test_category.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/categories/{test_category.id}")
        assert response.status_code == 404


# --- Tag Tests ---

class TestTags:
    """Test tag endpoints."""

    def test_list_tags_empty(self, client):
        """Returns empty list when no tags."""
        response = client.get("/api/tags")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tags(self, client, test_tag):
        """Returns all tags."""
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "New Arrival"

    def test_list_tags_by_type(self, client, test_tag, db_session):
        """Can filter tags by type."""
        # Add another tag with different type
        db_session.add(Tag(name="Sale", slug="sale", tag_type="promo"))
        db_session.commit()

        response = client.get("/api/tags?tag_type=badge")
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "new-arrival"

    def test_create_tag_admin(self, client, admin_headers):
        """Admins can create tags."""
        response = client.post(
            "/api/tags",
            headers=admin_headers,
            json={"name": "Bestseller", "slug": "bestseller", "tag_type": "badge"},
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Bestseller"

    def test_create_tag_duplicate_slug(self, client, admin_headers, test_tag):
        """Cannot create tag with existing slug."""
        response = client.post(
            "/api/tags",
            headers=admin_headers,
            json={"name": "Another", "slug": test_tag.slug},
        )
        assert response.status_code == 400

    def test_delete_tag(self, client, admin_headers, test_tag):
        """Admins can delete tags."""
        response = client.delete(f"/api/tags/{test_tag.id}", headers=admin_headers)
        assert response.status_code == 204

    def test_assign_tags_to_product(self, client, admin_headers, test_product, test_tag):
        """Can assign tags to products."""
        response = client.put(
            f"/api/products/{test_product.id}/tags",
            headers=admin_headers,
            json={"tag_ids": [test_tag.id]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_tag.id


# --- Collection Tests ---

class TestCollections:
    """Test collection endpoints."""

    def test_list_collections_empty(self, client):
        """Returns empty list when no collections."""
        response = client.get("/api/collections")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_collections(self, client, test_collection):
        """Returns all active collections."""
        response = client.get("/api/collections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Summer Sale"

    def test_get_collection_by_slug(self, client, test_collection):
        """Get collection by slug."""
        response = client.get(f"/api/collections/{test_collection.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Summer Sale"
        assert "products" in data
        assert "is_currently_active" in data

    def test_get_collection_not_found(self, client):
        """Returns 404 for nonexistent collection."""
        response = client.get("/api/collections/nonexistent")
        assert response.status_code == 404

    def test_create_collection_admin(self, client, admin_headers):
        """Admins can create collections."""
        response = client.post(
            "/api/collections",
            headers=admin_headers,
            json={
                "name": "Winter Collection",
                "slug": "winter-collection",
                "description": "Cold weather essentials",
            },
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Winter Collection"

    def test_create_collection_with_dates(self, client, admin_headers):
        """Can create time-limited collection."""
        response = client.post(
            "/api/collections",
            headers=admin_headers,
            json={
                "name": "Flash Sale",
                "slug": "flash-sale",
                "start_date": "2025-06-01T00:00:00Z",
                "end_date": "2025-06-02T00:00:00Z",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["start_date"] is not None
        assert data["end_date"] is not None

    def test_update_collection(self, client, admin_headers, test_collection):
        """Admins can update collections."""
        response = client.patch(
            f"/api/collections/{test_collection.id}",
            headers=admin_headers,
            json={"name": "Updated Summer Sale", "is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Summer Sale"
        assert response.json()["is_active"] is False

    def test_delete_collection(self, client, admin_headers, test_collection):
        """Admins can delete collections."""
        response = client.delete(
            f"/api/collections/{test_collection.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

    def test_add_products_to_collection(self, client, admin_headers, test_collection, test_product):
        """Can add products to collection."""
        response = client.post(
            f"/api/collections/{test_collection.id}/products",
            headers=admin_headers,
            json={"product_ids": [test_product.id]},
        )
        assert response.status_code == 200

        # Verify product in collection
        response = client.get(f"/api/collections/{test_collection.slug}")
        assert len(response.json()["products"]) == 1

    def test_remove_product_from_collection(
        self, client, admin_headers, test_collection, test_product, db_session
    ):
        """Can remove product from collection."""
        from shopmind.models.catalog import CollectionProduct

        # Add product to collection first
        db_session.add(CollectionProduct(
            collection_id=test_collection.id,
            product_id=test_product.id,
        ))
        db_session.commit()

        response = client.delete(
            f"/api/collections/{test_collection.id}/products/{test_product.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204


# --- Product Category Assignment ---

class TestProductCategoryAssignment:
    """Test assigning categories to products."""

    def test_assign_categories_to_product(self, client, admin_headers, test_product, test_category):
        """Can assign categories to products."""
        response = client.put(
            f"/api/products/{test_product.id}/categories",
            headers=admin_headers,
            json=[test_category.id],
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_category.id

    def test_product_appears_in_category(
        self, client, admin_headers, test_product, test_category
    ):
        """Product appears in category after assignment."""
        # Assign category
        client.put(
            f"/api/products/{test_product.id}/categories",
            headers=admin_headers,
            json=[test_category.id],
        )

        # Check category includes product
        response = client.get(f"/api/categories/{test_category.id}")
        products = response.json()["products"]
        assert len(products) == 1
        assert products[0]["id"] == test_product.id
