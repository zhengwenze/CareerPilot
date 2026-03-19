from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserProfile
from app.schemas.profile import UserProfileUpdateRequest


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


async def get_or_create_user_profile(session: AsyncSession, user: User) -> UserProfile:
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is not None:
        return profile

    profile = UserProfile(
        user_id=user.id,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def update_user_profile(
    session: AsyncSession,
    user: User,
    payload: UserProfileUpdateRequest,
) -> UserProfile:
    profile = await get_or_create_user_profile(session, user)

    user.nickname = _normalize_optional_text(payload.nickname)
    profile.job_direction = _normalize_optional_text(payload.job_direction)
    profile.target_city = _normalize_optional_text(payload.target_city)
    profile.target_role = _normalize_optional_text(payload.target_role)
    profile.updated_by = user.id
    if profile.created_by is None:
        profile.created_by = user.id

    session.add(user)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
