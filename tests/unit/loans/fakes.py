"""Shared fakes for loans unit tests."""

from __future__ import annotations

from loans.domain.email import Email
from loans.domain.ports import UserRepository
from loans.domain.user import User


class InMemoryUsers(UserRepository):
    """In-memory fake of the UserRepository port.

    Users are keyed by their email, which is the unique identity of an
    account.
    """

    def __init__(self) -> None:
        """Start with an empty account base."""
        self.users: dict[str, User] = {}

    async def get_by_email(self, email: Email) -> User | None:
        """Return the user for the email, or None when not present."""
        return self.users.get(email.value)

    async def save(self, user: User) -> None:
        """Insert a user into the in-memory account base."""
        self.users[user.email.value] = user

    async def count(self) -> int:
        """Return the total number of users."""
        return len(self.users)
