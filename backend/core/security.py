import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from models.api_key import APIKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)

API_KEY_PREFIX = "srq_"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def generate_api_key() -> str:
    """Generate a random API key with prefix."""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of an API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def _get_user_from_jwt(token: str, db: AsyncSession) -> User | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def _get_user_from_api_key(raw_key: str, db: AsyncSession) -> User | None:
    key_hash = hash_api_key(raw_key)
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True))
    api_key = result.scalar_one_or_none()
    if not api_key:
        return None
    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None
    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    await db.commit()
    # Load user
    user_result = await db.execute(select(User).where(User.id == api_key.user_id))
    return user_result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via JWT Bearer token OR X-API-Key header."""
    # Try JWT first
    if credentials and credentials.credentials:
        user = await _get_user_from_jwt(credentials.credentials, db)
        if user:
            return user

    # Try X-API-Key header
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        user = await _get_user_from_api_key(api_key_header, db)
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")
