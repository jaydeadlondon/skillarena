from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.activity import add_heartbeat_activity
from app.services.streaks import sync_user_streak

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityHeartbeat(BaseModel):
    activity_type: str = Field(default="general", max_length=40)
    seconds: int = Field(default=0, ge=0, le=60)
    reference_id: int | None = None
    path: str | None = Field(default=None, max_length=300)


@router.post("/heartbeat")
async def activity_heartbeat(
    payload: ActivityHeartbeat,
    db: DbSession,
    user: User = Depends(require_user),
) -> dict[str, str]:
    await add_heartbeat_activity(
        db,
        user,
        payload.activity_type,
        payload.seconds,
        payload.reference_id,
    )
    if payload.activity_type == "lesson":
        await sync_user_streak(db, user)
    await db.commit()
    return {"status": "ok"}
