"""
Authentication service.

Handles user registration, login, and JWT token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from shopmind.config import get_settings
from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.schemas.user import UserCreate, TokenPayload

settings = get_settings()

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: The user's database ID

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub"))
        exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        return TokenPayload(sub=user_id, exp=exp)
    except (JWTError, ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# --- User Operations ---

def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Find a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user account.

    Args:
        db: Database session
        user_data: User registration data

    Returns:
        Created user instance

    Raises:
        HTTPException: If email already exists
    """
    # Check for existing user
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # TODO: Emit UserRegistered event
    # event_bus.emit(UserRegistered(user_id=user.id, email=user.email))

    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Verify user credentials.

    Returns:
        User if credentials valid, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


# --- Dependencies for Route Protection ---

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Dependency that extracts and validates the current user from JWT.

    Usage:
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            ...
    """
    token_data = decode_token(token)
    user = get_user_by_id(db, token_data.sub)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False))],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """
    Optional user dependency - returns None if not authenticated.

    Use this for endpoints that work for both authenticated and anonymous users.
    """
    if not token:
        return None

    try:
        token_data = decode_token(token)
        user = get_user_by_id(db, token_data.sub)
        if user and user.is_active:
            return user
    except HTTPException:
        pass

    return None


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that requires the current user to be an admin.

    Usage:
        @app.get("/admin-only")
        def admin_route(user: User = Depends(get_current_admin)):
            ...
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
