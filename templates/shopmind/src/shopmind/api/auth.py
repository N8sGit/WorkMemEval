"""
Authentication API endpoints.

Provides user registration, login, and profile access.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.schemas.user import UserCreate, UserResponse, Token
from shopmind.services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: At least 8 characters
    - **full_name**: Optional display name
    """
    return create_user(db, user_data)


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """
    Authenticate and receive an access token.

    Uses OAuth2 password flow - send credentials as form data:
    - **username**: Email address
    - **password**: Account password

    Returns a JWT bearer token for authenticated requests.
    """
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current authenticated user's profile.

    Requires a valid JWT bearer token.
    """
    return user
