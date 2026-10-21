import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import jwt
import bcrypt
if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")
    bcrypt.__about__ = _About()

from fastapi import Depends, HTTPException, status, Request
import re
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from app import database

# Load environment variables from .env file
def _load_env():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

# Configuration from Environment Variables
SECRET_KEY = os.getenv("SECRET_KEY", "phase5-super-secret-jwt-key-ocr-image-search-2026-prod")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class UserRegister(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int
    is_admin: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    request: Request = None,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Multi-Tenant Row-Level Authentication Dependency:
    1. If JWT Bearer token is provided: validates signature and returns authenticated user.
    2. If no token, checks for client-supplied 'X-Guest-Session-ID' header or query param.
       Maps that session ID to a dedicated, isolated guest user account (never shared).
    3. If neither token nor guest session ID is present, returns an isolated ephemeral anonymous user
       with user_id = -1 (strictly empty vault, zero access to other users' documents).
    """
    if token:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            if username is None or user_id is None:
                raise credentials_exception
            user = database.get_user_by_id(user_id)
            if user is None:
                raise credentials_exception
            return user
        except jwt.PyJWTError:
            raise credentials_exception

    # Check for stable client-specific Guest Session ID (e.g. from unique mobile app installation)
    if request is not None:
        guest_sess_id = (
            request.headers.get("X-Guest-Session-ID")
            or request.headers.get("x-guest-session-id")
            or request.query_params.get("guest_session_id")
        )
        if guest_sess_id:
            clean_sess = guest_sess_id.strip()
            if 8 <= len(clean_sess) <= 128 and re.match(r"^[a-zA-Z0-9_\-]+$", clean_sess):
                return database.get_or_create_guest_user(clean_sess)

    # Completely unauthenticated request with no guest session:
    # Isolated anonymous entity with user_id = -1 (prevents global data leakage)
    return {"id": -1, "username": "anonymous_guest", "is_admin": False}


def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Admin-only dependency ensuring current user has admin privileges (Role-Based Access Control)."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden: Admin privileges required."
        )
    return current_user

