"""Tests for product search and filtering."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from shopmind.models.product import Product, ProductVariant
from shopmind.models.catalog import Category, Tag, ProductCategory, ProductTag


# --- Fixtures ---


@pytest.fixture
def search_products(db_session):
    """Create multiple products for search testing."""
    products = []

    # Product 1: Electronics - Phone (in stock, on sale)
    p1 = Product(
        name="Smartphone Pro",
        slug="smartphone-pro",
        description="A powerful smartphone with amazing features",
        base_price=Decimal("999.99"),
        has_variants=True,
        is_active=True,
    )
    db_session.add(p1)
    db_session.flush()

    v1 = ProductVariant(
        product_id=p1.id,
        sku="SP-128-BLK",
        attributes={"storage": "128GB", "color": "black"},
        stock_quantity=50,
        sale_price=Decimal("899.99"),
        sale_start=datetime.now() - timedelta(days=1),
        sale_end=datetime.now() + timedelta(days=30),
    )
    db_session.add(v1)
    products.append(p1)

    # Product 2: Electronics - Headphones (in stock, not on sale)
    p2 = Product(
        name="Wireless Headphones",
        slug="wireless-headphones",
        description="Premium wireless headphones with noise cancellation",
        base_price=Decimal("299.99"),
        has_variants=True,
        is_active=True,
    )
    db_session.add(p2)
    db_session.flush()

    v2 = ProductVariant(
        product_id=p2.id,
        sku="WH-BLK",
        attributes={"color": "black"},
        stock_quantity=25,
    )
    db_session.add(v2)
    products.append(p2)

    # Product 3: Clothing - T-Shirt (out of stock)
    p3 = Product(
        name="Cotton T-Shirt",
        slug="cotton-tshirt",
        description="Comfortable cotton t-shirt for everyday wear",
        base_price=Decimal("29.99"),
        has_variants=True,
        is_active=True,
    )
    db_session.add(p3)
    db_session.flush()

    v3 = ProductVariant(
        product_id=p3.id,
        sku="TS-M-WHT",
        attributes={"size": "M", "color": "white"},
        stock_quantity=0,  # Out of stock
    )
    db_session.add(v3)
    products.append(p3)

    # Product 4: Clothing - Jeans (in stock)
    p4 = Product(
        name="Slim Fit Jeans",
        slug="slim-fit-jeans",
        description="Classic slim fit denim jeans",
        base_price=Decimal("79.99"),
        has_variants=True,
        is_active=True,
    )
    db_session.add(p4)
    db_session.flush()

    v4 = ProductVariant(
        product_id=p4.id,
        sku="JN-32-BLU",
        attributes={"size": "32", "color": "blue"},
        stock_quantity=15,
    )
    db_session.add(v4)
    products.append(p4)

    # Product 5: Inactive product (should not appear in search)
    p5 = Product(
        name="Discontinued Item",
        slug="discontinued-item",
        description="This product is no longer available",
        base_price=Decimal("49.99"),
        is_active=False,
    )
    db_session.add(p5)
    products.append(p5)

    db_session.commit()
    return products


@pytest.fixture
def search_categories(db_session):
    """Create categories for filtering tests."""
    electronics = Category(name="Electronics", slug="electronics")
    clothing = Category(name="Clothing", slug="clothing")
    db_session.add(electronics)
    db_session.add(clothing)
    db_session.commit()
    db_session.refresh(electronics)
    db_session.refresh(clothing)
    return {"electronics": electronics, "clothing": clothing}


@pytest.fixture
def search_tags(db_session):
    """Create tags for filtering tests."""
    new_arrival = Tag(name="New Arrival", slug="new-arrival", tag_type="badge")
    bestseller = Tag(name="Bestseller", slug="bestseller", tag_type="badge")
    db_session.add(new_arrival)
    db_session.add(bestseller)
    db_session.commit()
    db_session.refresh(new_arrival)
    db_session.refresh(bestseller)
    return {"new_arrival": new_arrival, "bestseller": bestseller}


@pytest.fixture
def products_with_categories(db_session, search_products, search_categories):
    """Assign categories to products."""
    electronics = search_categories["electronics"]
    clothing = search_categories["clothing"]

    # Phone and Headphones -> Electronics
    db_session.add(ProductCategory(product_id=search_products[0].id, category_id=electronics.id))
    db_session.add(ProductCategory(product_id=search_products[1].id, category_id=electronics.id))

    # T-Shirt and Jeans -> Clothing
    db_session.add(ProductCategory(product_id=search_products[2].id, category_id=clothing.id))
    db_session.add(ProductCategory(product_id=search_products[3].id, category_id=clothing.id))

    db_session.commit()
    return search_products


@pytest.fixture
def products_with_tags(db_session, search_products, search_tags):
    """Assign tags to products."""
    new_arrival = search_tags["new_arrival"]
    bestseller = search_tags["bestseller"]

    # Phone is new arrival and bestseller
    db_session.add(ProductTag(product_id=search_products[0].id, tag_id=new_arrival.id))
    db_session.add(ProductTag(product_id=search_products[0].id, tag_id=bestseller.id))

    # Headphones is bestseller
    db_session.add(ProductTag(product_id=search_products[1].id, tag_id=bestseller.id))

    # T-Shirt is new arrival
    db_session.add(ProductTag(product_id=search_products[2].id, tag_id=new_arrival.id))

    db_session.commit()
    return search_products


# --- Basic Search Tests ---


class TestBasicSearch:
    """Test basic search functionality."""

    def test_search_no_params(self, client, search_products):
        """Search without params returns all active products."""
        response = client.get("/api/products/search")
        assert response.status_code == 200
        data = response.json()
        # Should return 4 products (excluding inactive)
        assert data["total"] == 4
        assert len(data["items"]) == 4

    def test_search_by_text(self, client, search_products):
        """Search by text query."""
        response = client.get("/api/products/search?q=smartphone")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "smartphone-pro"
        assert data["query"] == "smartphone"

    def test_search_by_description(self, client, search_products):
        """Search matches product descriptions."""
        response = client.get("/api/products/search?q=noise cancellation")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "wireless-headphones"

    def test_search_case_insensitive(self, client, search_products):
        """Search is case insensitive."""
        response = client.get("/api/products/search?q=SMARTPHONE")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_search_partial_match(self, client, search_products):
        """Search matches partial words."""
        response = client.get("/api/products/search?q=wire")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["slug"] == "wireless-headphones"

    def test_search_no_results(self, client, search_products):
        """Search with no matches returns empty."""
        response = client.get("/api/products/search?q=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# --- Category Filter Tests ---


class TestCategoryFilter:
    """Test filtering by category."""

    def test_filter_by_category_id(self, client, products_with_categories, search_categories):
        """Filter products by category ID."""
        cat_id = search_categories["electronics"].id
        response = client.get(f"/api/products/search?category_id={cat_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        slugs = {item["slug"] for item in data["items"]}
        assert slugs == {"smartphone-pro", "wireless-headphones"}

    def test_filter_by_category_slug(self, client, products_with_categories):
        """Filter products by category slug."""
        response = client.get("/api/products/search?category=clothing")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        slugs = {item["slug"] for item in data["items"]}
        assert slugs == {"cotton-tshirt", "slim-fit-jeans"}

    def test_filter_nonexistent_category(self, client, products_with_categories):
        """Filter by nonexistent category returns no results."""
        response = client.get("/api/products/search?category=nonexistent")
        assert response.status_code == 200
        assert response.json()["total"] == 0


# --- Tag Filter Tests ---


class TestTagFilter:
    """Test filtering by tags."""

    def test_filter_by_single_tag(self, client, products_with_tags):
        """Filter products by single tag."""
        response = client.get("/api/products/search?tags=bestseller")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        slugs = {item["slug"] for item in data["items"]}
        assert slugs == {"smartphone-pro", "wireless-headphones"}

    def test_filter_by_multiple_tags(self, client, products_with_tags):
        """Filter by multiple tags (AND logic)."""
        response = client.get("/api/products/search?tags=new-arrival,bestseller")
        assert response.status_code == 200
        data = response.json()
        # Only phone has both tags
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "smartphone-pro"

    def test_filter_nonexistent_tag(self, client, products_with_tags):
        """Filter by nonexistent tag returns no results."""
        response = client.get("/api/products/search?tags=nonexistent")
        assert response.status_code == 200
        assert response.json()["total"] == 0


# --- Price Filter Tests ---


class TestPriceFilter:
    """Test filtering by price range."""

    def test_filter_min_price(self, client, search_products):
        """Filter by minimum price."""
        response = client.get("/api/products/search?min_price=100")
        assert response.status_code == 200
        data = response.json()
        # Only phone and headphones cost >= 100
        assert data["total"] == 2

    def test_filter_max_price(self, client, search_products):
        """Filter by maximum price."""
        response = client.get("/api/products/search?max_price=50")
        assert response.status_code == 200
        data = response.json()
        # Only t-shirt costs <= 50
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "cotton-tshirt"

    def test_filter_price_range(self, client, search_products):
        """Filter by price range."""
        response = client.get("/api/products/search?min_price=50&max_price=300")
        assert response.status_code == 200
        data = response.json()
        # Jeans (79.99) and Headphones (299.99)
        assert data["total"] == 2


# --- Stock Filter Tests ---


class TestStockFilter:
    """Test filtering by stock status."""

    def test_filter_in_stock(self, client, search_products):
        """Filter to only in-stock products."""
        response = client.get("/api/products/search?in_stock=true")
        assert response.status_code == 200
        data = response.json()
        # 3 products in stock (phone, headphones, jeans), t-shirt is out
        assert data["total"] == 3
        slugs = {item["slug"] for item in data["items"]}
        assert "cotton-tshirt" not in slugs


# --- Sale Filter Tests ---


class TestSaleFilter:
    """Test filtering by sale status."""

    def test_filter_on_sale(self, client, search_products):
        """Filter to only products on sale."""
        response = client.get("/api/products/search?on_sale=true")
        assert response.status_code == 200
        data = response.json()
        # Only phone is on sale
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "smartphone-pro"


# --- Combined Filter Tests ---


class TestCombinedFilters:
    """Test combining multiple filters."""

    def test_search_with_category(self, client, products_with_categories):
        """Combine text search with category filter."""
        response = client.get("/api/products/search?q=wireless&category=electronics")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "wireless-headphones"

    def test_category_with_price(self, client, products_with_categories):
        """Combine category with price filter."""
        response = client.get("/api/products/search?category=electronics&max_price=500")
        assert response.status_code == 200
        data = response.json()
        # Only headphones (299.99), phone (999.99) is too expensive
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "wireless-headphones"

    def test_multiple_filters(
        self, client, products_with_categories, products_with_tags, search_categories, search_tags
    ):
        """Combine many filters."""
        # Electronics + in stock + bestseller
        response = client.get(
            "/api/products/search?category=electronics&in_stock=true&tags=bestseller"
        )
        assert response.status_code == 200
        data = response.json()
        # Phone and headphones are both in electronics and bestseller and in stock
        assert data["total"] == 2


# --- Pagination Tests ---


class TestSearchPagination:
    """Test search pagination."""

    def test_pagination_page_size(self, client, search_products):
        """Respects page_size parameter."""
        response = client.get("/api/products/search?page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 4
        assert data["pages"] == 2
        assert data["page"] == 1

    def test_pagination_second_page(self, client, search_products):
        """Can fetch second page."""
        response = client.get("/api/products/search?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2


# --- Facet Tests ---


class TestSearchFacets:
    """Test facet response."""

    def test_facets_included_by_default(self, client, search_products):
        """Facets are included by default."""
        response = client.get("/api/products/search")
        assert response.status_code == 200
        data = response.json()
        assert "facets" in data
        assert "price_range" in data["facets"]
        assert "in_stock_count" in data["facets"]
        assert "on_sale_count" in data["facets"]

    def test_facets_price_range(self, client, search_products):
        """Facets include correct price range."""
        response = client.get("/api/products/search")
        data = response.json()
        price_range = data["facets"]["price_range"]
        # Min is t-shirt (29.99), max is phone (999.99)
        assert float(price_range["min"]) == 29.99
        assert float(price_range["max"]) == 999.99

    def test_facets_stock_count(self, client, search_products):
        """Facets include correct stock count."""
        response = client.get("/api/products/search")
        data = response.json()
        # 3 products in stock
        assert data["facets"]["in_stock_count"] == 3

    def test_facets_sale_count(self, client, search_products):
        """Facets include correct sale count."""
        response = client.get("/api/products/search")
        data = response.json()
        # 1 product on sale
        assert data["facets"]["on_sale_count"] == 1

    def test_facets_categories(self, client, products_with_categories, search_categories):
        """Facets include category counts."""
        response = client.get("/api/products/search")
        data = response.json()
        categories = data["facets"]["categories"]
        assert len(categories) == 2
        # Check counts
        cat_counts = {c["slug"]: c["count"] for c in categories}
        assert cat_counts["electronics"] == 2
        assert cat_counts["clothing"] == 2

    def test_facets_tags(self, client, products_with_tags, search_tags):
        """Facets include tag counts."""
        response = client.get("/api/products/search")
        data = response.json()
        tags = data["facets"]["tags"]
        assert len(tags) == 2
        # Check counts
        tag_counts = {t["slug"]: t["count"] for t in tags}
        assert tag_counts["new-arrival"] == 2  # phone, tshirt
        assert tag_counts["bestseller"] == 2  # phone, headphones

    def test_facets_can_be_disabled(self, client, search_products):
        """Facets can be disabled."""
        response = client.get("/api/products/search?include_facets=false")
        assert response.status_code == 200
        data = response.json()
        # Facets should be empty when disabled
        assert data["facets"]["categories"] == []
        assert data["facets"]["tags"] == []
        assert data["facets"]["price_range"] is None

    def test_facets_update_with_filters(self, client, products_with_categories, search_categories):
        """Facets reflect filtered results."""
        # Filter to electronics only
        response = client.get("/api/products/search?category=electronics")
        data = response.json()
        # Clothing category should not appear in facets (0 matching products)
        cat_slugs = {c["slug"] for c in data["facets"]["categories"]}
        assert "clothing" not in cat_slugs


# --- Search Result Data Tests ---


class TestSearchResultData:
    """Test search result data structure."""

    def test_result_includes_price_range(self, client, search_products):
        """Results include min/max price from variants."""
        response = client.get("/api/products/search?q=smartphone")
        data = response.json()
        item = data["items"][0]
        # Phone has sale price 899.99
        assert "min_price" in item
        assert "max_price" in item

    def test_result_includes_stock_status(self, client, search_products):
        """Results include is_in_stock flag."""
        response = client.get("/api/products/search")
        data = response.json()
        for item in data["items"]:
            assert "is_in_stock" in item

    def test_result_includes_sale_status(self, client, search_products):
        """Results include is_on_sale flag."""
        response = client.get("/api/products/search?q=smartphone")
        data = response.json()
        item = data["items"][0]
        assert item["is_on_sale"] is True

    def test_result_includes_category_ids(self, client, products_with_categories):
        """Results include category_ids."""
        response = client.get("/api/products/search?q=smartphone")
        data = response.json()
        item = data["items"][0]
        assert "category_ids" in item
        assert len(item["category_ids"]) == 1

    def test_result_includes_tag_slugs(self, client, products_with_tags):
        """Results include tag_slugs."""
        response = client.get("/api/products/search?q=smartphone")
        data = response.json()
        item = data["items"][0]
        assert "tag_slugs" in item
        assert "new-arrival" in item["tag_slugs"]
        assert "bestseller" in item["tag_slugs"]
