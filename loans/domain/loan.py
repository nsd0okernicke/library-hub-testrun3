"""Loan entity for the loan service."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date, timedelta

from loans.domain.isbn import Isbn

#: The global loan term in days. A single configuration value shared by all
#: loans; it is not overridable per borrow request.
LOAN_TERM_DAYS = 28


class InvalidLoanDataError(ValueError):
    """Raised when loan record data violates loan service rules."""


class LoanStatus(enum.Enum):
    """Lifecycle of a loan: requested, then active or rejected, and returned."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"


class LoanNotPendingError(Exception):
    """Raised when settling a loan that is no longer PENDING."""

    def __init__(self, loan_id: str, status: LoanStatus) -> None:
        """Create the error, remembering the loan and its status."""
        super().__init__(f"loan {loan_id} is {status.value}, not PENDING")
        self.loan_id = loan_id
        self.status = status


class LoanNotActiveError(Exception):
    """Raised when returning a loan that is not ACTIVE."""

    def __init__(self, loan_id: str, status: LoanStatus) -> None:
        """Create the error, remembering the loan and its status."""
        super().__init__(f"loan {loan_id} is {status.value}, not ACTIVE")
        self.loan_id = loan_id
        self.status = status


class LoanNotFoundError(Exception):
    """Raised when a loan id names no stored loan record."""

    def __init__(self, loan_id: str) -> None:
        """Create the error, remembering the offending loan id."""
        super().__init__(f"loan {loan_id} not found")
        self.loan_id = loan_id


@dataclass(slots=True)
class Loan:
    """A book loan: user, isbn, request date and reservation outcome.

    The loan is created in status PENDING when the borrow request is accepted.
    Filling the reservation activates it with a due date of the request date
    plus the global loan term; rejecting it leaves it queryable in status
    REJECTED with no due date. An ACTIVE loan may be returned; the due date
    stays on the loan in status RETURNED, which is also queryable.
    """

    loan_id: str
    user_id: str
    isbn: Isbn
    requested_on: date
    status: LoanStatus = LoanStatus.PENDING
    due_date: date | None = None

    def __post_init__(self) -> None:
        if not self.loan_id:
            raise InvalidLoanDataError("loan_id must not be empty")
        if not self.user_id:
            raise InvalidLoanDataError("user_id must not be empty")
        if self.isbn is None:
            raise InvalidLoanDataError("isbn must not be empty")
        if self.requested_on is None:
            raise InvalidLoanDataError("requested_on must not be empty")

    def _require_pending(self) -> None:
        """Refuse settlement of a loan that has already been settled."""
        if self.status is not LoanStatus.PENDING:
            raise LoanNotPendingError(self.loan_id, self.status)

    def _require_active(self) -> None:
        """Refuse returning a loan that has not been fulfilled."""
        if self.status is not LoanStatus.ACTIVE:
            raise LoanNotActiveError(self.loan_id, self.status)

    def mark_returned(self) -> None:
        """Mark an ACTIVE loan as returned, keeping its due date."""
        self._require_active()
        self.status = LoanStatus.RETURNED

    def fulfill(self) -> None:
        """Mark the reservation as fulfilled: ACTIVE with a due date.

        The due date is the borrow request date plus the global loan term.
        """
        self._require_pending()
        self.status = LoanStatus.ACTIVE
        self.due_date = self.requested_on + timedelta(days=LOAN_TERM_DAYS)

    def reject(self) -> None:
        """Mark the reservation as rejected: REJECTED with no due date."""
        self._require_pending()
        self.status = LoanStatus.REJECTED
        self.due_date = None
