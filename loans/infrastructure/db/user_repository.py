"""SQLAlchemy implementation of the UserRepository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from loans.domain.email import Email
from loans.domain.ports import UserRepository
from loans.domain.user import User
from loans.infrastructure.db.models import UserRow


def _to_domain(row: UserRow) -> User:
    """Map an ORM row to the User domain entity."""
    return User(user_id=row.user_id, name=row.name, email=Email(row.email))


class SqlAlchemyUserRepository(UserRepository):
    """Persists user accounts in PostgreSQL through SQLAlchemy (asyncpg driver)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind the repository to a session factory."""
        self._sessions = sessions

    async def get_by_email(self, email: Email) -> User | None:
        """Return the user for the email, or None when not present."""
        async with self._sessions() as session:
            result = await session.execute(select(UserRow).where(UserRow.email == email.value))
            row = result.scalar_one_or_none()
            return _to_domain(row) if row is not None else None

    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user for the system-generated user id, or None."""
        async with self._sessions() as session:
            result = await session.execute(select(UserRow).where(UserRow.user_id == user_id))
            row = result.scalar_one_or_none()
            return _to_domain(row) if row is not None else None

    async def save(self, user: User) -> None:
        """Insert a new user into the account base."""
        row = UserRow(user_id=user.user_id, name=user.name, email=user.email.value)
        async with self._sessions() as session:
            session.add(row)
            await session.commit()

    async def count(self) -> int:
        """Return the total number of users."""
        async with self._sessions() as session:
            result = await session.scalar(select(func.count()).select_from(UserRow))
            return int(result or 0)
