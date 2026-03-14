from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import User


class UserAlreadyExistsError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    statement = select(User).where(User.email == normalize_email(email))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    nickname: str | None,
) -> User:
    existing_user = await get_user_by_email(session, email)
    if existing_user is not None:
        raise UserAlreadyExistsError("A user with this email already exists")

    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        nickname=nickname,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    if user.status != "active":
        raise AuthenticationError("User account is disabled")
    return user
