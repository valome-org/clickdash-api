from datetime import timedelta
from typing import List

from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_active_user, get_current_admin_user
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv
from models.auth import (PasswordChange, Token, UserCreate, UserLogin,
                         UserResponse)
from services.auth_service import AuthService
from sqlalchemy.orm import Session
from utils.serialization import CustomJSONResponse

router = APIRouter()
auth_service = AuthService()

# Google OAuth2 configuration
load_dotenv()
CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Remove in production


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user = auth_service.create_user(db, user_data)
        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = auth_service.authenticate_user(
        db, user_credentials.username, user_credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    user_response = UserResponse(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat()
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    success = auth_service.change_password(
        db, current_user, password_data.current_password, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    return CustomJSONResponse(content={"message": "Password changed successfully"})


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    return [
        UserResponse(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active_status(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle user active status (admin only)"""
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = not user.is_active
    db.commit()

    return CustomJSONResponse(content={
        "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
        "user_id": user.user_id,
        "is_active": user.is_active
    })


@router.get("/google")
async def google_auth(request: Request):
    """Start Google OAuth2 flow (stateless)"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=str(request.url_for("google_oauth2callback")),
        )
        auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
        )
        return RedirectResponse(auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth2 flow error: {str(e)}")


@router.get("/google/callback", name="google_oauth2callback")
async def google_oauth2callback(request: Request, state: str = None):
    """Handle Google OAuth2 callback (stateless) and redirect to frontend with credentials as URL param."""
    import json
    import urllib.parse
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=str(request.url_for("google_oauth2callback")),
        )
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        cred_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        cred_str = urllib.parse.quote(json.dumps(cred_dict))
        frontend_url = f"http://localhost:3000/upload?credentials={cred_str}"
        return RedirectResponse(frontend_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth2 callback error: {str(e)}")
