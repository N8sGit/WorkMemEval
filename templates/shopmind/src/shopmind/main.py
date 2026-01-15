"""
ShopMind FastAPI application entry point.

Run with:
    uvicorn shopmind.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shopmind.config import get_settings
from shopmind.database import init_db
from shopmind.api import auth, products, cart, orders, catalog, promotions, customer, reviews, shipping, returns, shipments

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Startup: Initialize database tables
    Shutdown: Cleanup resources
    """
    # Startup
    print(f"Starting {settings.app_name}...")
    init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="""
ShopMind is an intelligent e-commerce platform with features for:

- **User authentication** - JWT-based auth with role-based access
- **Product catalog** - Products with flexible variants (size, color, etc.)
- **Categories & Tags** - Hierarchical categories and flexible tagging
- **Collections** - Curated product groups with time-based activation
- **Shopping cart** - Session-based and user-linked carts
- **Checkout & Orders** - Stock validation, order creation, status tracking
- **Inventory management** - Stock tracking with automatic deduction
- **Promotions** - Coupons, cart rules, sale prices, tiered pricing
- **Customer features** - Wishlist, recently viewed, saved addresses
- **Product search** - Full-text search with faceted filtering
- **Reviews & Ratings** - Product reviews with moderation
- **Back-in-stock** - Notification subscriptions
- **Shipping Methods** - Multiple shipping options with cost calculation
- **Guest Checkout** - Order without account creation
- **Gift Orders** - Gift messages and wrapping options
- **Returns & Refunds** - RMA workflow with stock restoration
- **Partial Fulfillment** - Multiple shipments per order with tracking

## Coming Soon

- Personalized recommendations
- Dynamic pricing
- Fraud detection
    """,
    version="0.9.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
# NOTE: In production, restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(promotions.router, prefix="/api")
app.include_router(customer.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(shipping.router, prefix="/api")
app.include_router(returns.router, prefix="/api")
app.include_router(shipments.router, prefix="/api")


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Actually check DB connection
    }
