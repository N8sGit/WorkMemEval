# ShopMind

An intelligent e-commerce platform with personalization and dynamic pricing capabilities.

## Status: Phase 1 - Foundation

This is an early-stage project implementing core e-commerce functionality with an architecture designed for future AI/ML features.

### What's Implemented

- **Authentication**: JWT-based user registration and login
- **Product Catalog**: Products with flexible variants (JSONB attributes)
- **Inventory Tracking**: Stock management with low-stock warnings
- **Event System**: In-memory event bus for decoupled architecture

### What's Coming

- [ ] Order management and checkout flow
- [ ] Payment processing integration
- [ ] Personalized recommendations
- [ ] Dynamic pricing engine
- [ ] Fraud detection heuristics
- [ ] Admin dashboard

## Tech Stack

- **Python 3.11+** - Modern Python with type hints
- **FastAPI** - Async web framework with automatic OpenAPI docs
- **SQLAlchemy 2.0** - ORM with native typing support
- **PostgreSQL** - Primary database (SQLite for local dev)
- **Pydantic** - Request/response validation
- **JWT** - Stateless authentication

## Quick Start

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Installation

```bash
# Clone the repository
cd Shopmind

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn shopmind.main:app --reload

# Server will start at http://localhost:8000
```

### API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

Settings are loaded from environment variables. Create a `.env` file:

```env
# Database (default: SQLite for local dev)
DATABASE_URL=sqlite:///./shopmind.db
# For PostgreSQL: DATABASE_URL=postgresql://user:pass@localhost/shopmind

# JWT Secret (change in production!)
SECRET_KEY=your-secret-key-here

# Debug mode
DEBUG=true
```

## Project Structure

```
src/shopmind/
├── main.py           # FastAPI app entry point
├── config.py         # Settings from environment
├── database.py       # SQLAlchemy setup
├── models/           # Database models
│   ├── user.py       # User accounts
│   └── product.py    # Products and variants
├── schemas/          # Pydantic request/response schemas
├── services/         # Business logic layer
│   ├── auth.py       # Authentication logic
│   └── catalog.py    # Product catalog operations
├── api/              # HTTP route handlers
│   ├── auth.py       # Auth endpoints
│   └── products.py   # Product CRUD endpoints
└── events/           # Event system
    └── base.py       # Event bus implementation
```

## API Examples

### Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret123"}'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secret123"
```

### Create a Product (Admin)

```bash
curl -X POST http://localhost:8000/api/products \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Classic T-Shirt",
    "slug": "classic-tshirt",
    "base_price": 29.99,
    "variants": [
      {"sku": "TSH-S-BLU", "attributes": {"size": "S", "color": "blue"}, "stock_quantity": 50},
      {"sku": "TSH-M-BLU", "attributes": {"size": "M", "color": "blue"}, "stock_quantity": 75}
    ]
  }'
```

## Architecture Decisions

### Why Modular Monolith?

We start with a modular monolith rather than microservices because:
1. Faster initial development
2. Easier refactoring during early iterations
3. Can extract services later when boundaries are clearer

### Why JSONB for Variant Attributes?

Different products have different attributes (size/color for clothing, capacity/color for phones). JSONB lets us:
- Avoid complex EAV patterns
- Query and index JSON fields in PostgreSQL
- Validate at the application layer

### Why Event-Driven?

The in-memory event bus prepares us for:
- Analytics pipelines (track user behavior)
- ML features (recommendations need view/purchase events)
- Decoupled services (order placed → inventory updated → email sent)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
ruff check src/ --fix
ruff format src/
```

## License

MIT
