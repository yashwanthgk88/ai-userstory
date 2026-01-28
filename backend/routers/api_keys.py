from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.api_key import APIKey
from schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyCreated
from core.security import get_current_user, generate_api_key, hash_api_key

router = APIRouter(tags=["api_keys"])


@router.post("/auth/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(req: APIKeyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_hash=hash_api_key(raw_key),
        name=req.name,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        key=raw_key,
    )


@router.get("/auth/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc()))
    return result.scalars().all()


@router.delete("/auth/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
