"""Port interfaces for the loan service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from loans.domain.email import Email
from loans.domain.events import DomainEvent
from loans.domain.loan import Loan
from loans.domain.user import User


class DomainEventPublisher(ABC):
    """Outbound port for publishing domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to interested consumers."""


class UserRepository(ABC):
    """Persistence port for user accounts.

    Identity is the email address: two accounts may not share an email.
    """

    @abstractmethod
    async def get_by_email(self, email: Email) -> User | None:
        """Return the user for the email, or None when not present."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user for the system-generated user id, or None."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Insert a new user into the account base."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of users."""


class LoanRepository(ABC):
    """Persistence port for loan records.

    Identity is the system-generated loan id.
    """

    @abstractmethod
    async def get(self, loan_id: str) -> Loan | None:
        """Return the loan for the loan id, or None when not present."""

    @abstractmethod
    async def save(self, loan: Loan) -> None:
        """Insert or update a loan record."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of loans."""

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Loan]:
        """Return every loan of the user, in any order."""

    @abstractmethod
    async def list_active(self) -> list[Loan]:
        """Return every ACTIVE loan, across all users, in any order."""
