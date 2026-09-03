"""Unit tests for the returned state of the Loan entity."""

from datetime import date, timedelta

import pytest

from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanNotActiveError, LoanNotPendingError, LoanStatus

ISBN = Isbn("978-0-20-163361-0")


def make_loan(**overrides: object) -> Loan:
    """Build a PENDING loan with fixed defaults, applying overrides."""
    fields: dict[str, object] = {
        "loan_id": "loan-1",
        "user_id": "user-1",
        "isbn": ISBN,
        "requested_on": date(2026, 9, 3),
    }
    fields.update(overrides)
    return Loan(**fields)  # type: ignore[arg-type]


def make_active_loan() -> Loan:
    """Build an ACTIVE loan with its 28-day due date."""
    loan = make_loan()
    loan.fulfill()
    return loan


def test_return_marks_loan_returned() -> None:
    """Returning a fulfilled loan moves it to RETURNED."""
    loan = make_active_loan()
    loan.mark_returned()
    assert loan.status is LoanStatus.RETURNED


def test_return_keeps_the_due_date() -> None:
    """The due date set at fulfillment stays on the loan after a return."""
    loan = make_active_loan()
    loan.mark_returned()
    assert loan.due_date == date(2026, 9, 3) + timedelta(days=28)


@pytest.mark.parametrize("outcome", ["fulfill", "reject"])
def test_only_an_active_loan_can_be_returned(outcome: str) -> None:
    """A loan that is not ACTIVE cannot be returned."""
    loan = make_loan()
    if outcome == "reject":
        loan.reject()
    with pytest.raises(LoanNotActiveError):
        loan.mark_returned()
    assert loan.status is not LoanStatus.RETURNED


def test_returned_loan_cannot_be_settled_again() -> None:
    """Once returned, the reservation is no longer settleable."""
    loan = make_active_loan()
    loan.mark_returned()
    with pytest.raises(LoanNotPendingError):
        loan.fulfill()
    assert loan.status is LoanStatus.RETURNED
