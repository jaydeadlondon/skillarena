from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import CurrencyTransaction, User


async def add_skill_points(
    db: AsyncSession,
    user: User,
    amount: int,
    reason: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> None:
    user.skill_points += amount
    db.add(
        CurrencyTransaction(
            user_id=user.id,
            amount=amount,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
        )
    )
