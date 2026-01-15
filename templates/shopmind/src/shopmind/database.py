"""
Database connection and session management.

Uses SQLAlchemy 2.0 style with async support ready for future migration.
For now, we use synchronous sessions for simplicity.
"""

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shopmind.config import get_settings

settings = get_settings()

# Create engine
# NOTE: For SQLite, check_same_thread=False is needed for FastAPI's threaded model
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,  # Log SQL in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    NOTE: This uses create_all for development. In production, use Alembic migrations.
    """
    from shopmind.models import Base
    Base.metadata.create_all(bind=engine)
