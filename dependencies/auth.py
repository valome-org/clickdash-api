from database.connection import get_db
from database.models import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.auth_service import AuthService
from sqlalchemy.orm import Session

# JWT token security scheme
security = HTTPBearer()
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        token_data = auth_service.verify_token(token)
        if token_data is None or token_data.username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = auth_service.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    if not getattr(user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not getattr(current_user, 'is_active', True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current admin user"""
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
