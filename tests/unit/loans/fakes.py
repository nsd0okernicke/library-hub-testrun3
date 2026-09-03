"""Shared fakes for loans unit tests."""

from __future__ import annotations

from loans.domain.email import Email
from loans.domain.loan import Loan
from loans.domain.ports import LoanRepository, UserRepository
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

    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user for the system-generated user id, or None."""
        return next((u for u in self.users.values() if u.user_id == user_id), None)

    async def save(self, user: User) -> None:
        """Insert a user into the in-memory account base."""
        self.users[user.email.value] = user

    async def count(self) -> int:
        """Return the total number of users."""
        return len(self.users)


class InMemoryLoans(LoanRepository):
    """In-memory fake of the LoanRepository port, keyed by loan id."""

    def __init__(self) -> None:
        """Start with no loan records."""
        self.loans: dict[str, Loan] = {}

    async def get(self, loan_id: str) -> Loan | None:
        """Return the loan for the loan id, or None when not present."""
        return self.loans.get(loan_id)

    async def save(self, loan: Loan) -> None:
        """Insert or update a loan record."""
        self.loans[loan.loan_id] = loan

    async def count(self) -> int:
        """Return the total number of loans."""
        return len(self.loans)
