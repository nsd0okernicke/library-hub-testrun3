"""Unit tests for the Loan.is_overdue domain rule."""

from datetime import date, timedelta

import pytest

from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus

ISBN = Isbn("978-0-20-163361-0")
TODAY = date(2026, 9, 3)


def make_loan(status: LoanStatus, due_date: date | None) -> Loan:
    """Build a loan in the given status with the given due date."""
    return Loan(
        loan_id="loan-1",
        user_id="user-1",
        isbn=ISBN,
        requested_on=TODAY - timedelta(days=28),
        status=status,
        due_date=due_date,
    )


def test_active_loan_past_due_date_is_overdue() -> None:
    """An ACTIVE loan whose due date lies before today is overdue."""
    loan = make_loan(LoanStatus.ACTIVE, TODAY - timedelta(days=1))
    assert loan.is_overdue(TODAY) is True


@pytest.mark.parametrize(
    "status",
    [LoanStatus.PENDING, LoanStatus.REJECTED, LoanStatus.RETURNED],
)
def test_non_active_loans_are_never_overdue(status: LoanStatus) -> None:
    """PENDING, REJECTED and RETURNED loans are never overdue, even past due."""
    loan = make_loan(status, TODAY - timedelta(days=10))
    assert loan.is_overdue(TODAY) is False


def test_active_loan_due_today_is_not_overdue() -> None:
    """The due date must lie strictly before the current day."""
    loan = make_loan(LoanStatus.ACTIVE, TODAY)
    assert loan.is_overdue(TODAY) is False


def test_active_loan_due_in_the_future_is_not_overdue() -> None:
    """An ACTIVE loan whose due date has not yet passed is not overdue."""
    loan = make_loan(LoanStatus.ACTIVE, TODAY + timedelta(days=5))
    assert loan.is_overdue(TODAY) is False


def test_active_loan_without_due_date_is_not_overdue() -> None:
    """Defensively: an ACTIVE loan missing its due date is not overdue."""
    loan = make_loan(LoanStatus.ACTIVE, None)
    assert loan.is_overdue(TODAY) is False
