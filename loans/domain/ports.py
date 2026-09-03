"""Port interfaces for the loan service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from loans.domain.email import Email
from loans.domain.user import User


class UserRepository(ABC):
    """Persistence port for user accounts.

    Identity is the email address: two accounts may not share an email.
    """

    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        """Return the user for the email, or None when not present."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Insert a new user into the account base."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of users."""
