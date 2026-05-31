from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DbSession) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await db.get(User, int(user_id))


async def require_user(
    current_user: Annotated[User | None, Depends(get_current_user)],
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/"}
        )
    return current_user


async def require_admin(current_user: Annotated[User, Depends(require_user)]) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required."
        )
    return current_user


async def user_by_steam_id(db: AsyncSession, steam_id: str) -> User | None:
    result = await db.execute(select(User).where(User.steam_id == steam_id))
    return result.scalar_one_or_none()
