"""Unit tests for the Loan domain entity."""

from collections.abc import Callable
from datetime import date, timedelta

import pytest

from loans.domain.isbn import Isbn
from loans.domain.loan import (
    LOAN_TERM_DAYS,
    InvalidLoanDataError,
    Loan,
    LoanNotPendingError,
    LoanStatus,
)

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


def test_new_loan_is_pending_with_no_due_date() -> None:
    """A loan record starts in PENDING without a due date."""
    loan = make_loan()
    assert loan.status is LoanStatus.PENDING
    assert loan.due_date is None


def test_fulfill_sets_active_and_due_date_28_days_after_request() -> None:
    """Fulfilling a pending loan activates it with a 28-day due date."""
    loan = make_loan()
    loan.fulfill()
    assert loan.status is LoanStatus.ACTIVE
    assert loan.due_date == date(2026, 9, 3) + timedelta(days=28)


def test_loan_term_is_a_single_global_value() -> None:
    """The loan term is one global configuration value of 28 days."""
    assert LOAN_TERM_DAYS == 28


def test_fulfill_over_28_days_after_request_date() -> None:
    """The due date anchors on the request date, not the fulfillment time."""
    loan = make_loan(requested_on=date(2026, 12, 15))
    loan.fulfill()
    assert loan.due_date == date(2027, 1, 12)


def test_reject_sets_rejected_with_no_due_date() -> None:
    """A rejected reservation leaves the loan in REJECTED with no due date."""
    loan = make_loan()
    loan.reject()
    assert loan.status is LoanStatus.REJECTED
    assert loan.due_date is None


@pytest.mark.parametrize(
    "first, second",
    [
        (Loan.fulfill, Loan.fulfill),
        (Loan.fulfill, Loan.reject),
        (Loan.reject, Loan.fulfill),
        (Loan.reject, Loan.reject),
    ],
)
def test_settled_loan_cannot_be_settled_again(
    first: Callable[[Loan], None], second: Callable[[Loan], None]
) -> None:
    """Only PENDING loans can be settled; a second settlement is refused."""
    loan = make_loan()
    first(loan)
    with pytest.raises(LoanNotPendingError):
        second(loan)
    assert loan.status is not LoanStatus.PENDING


@pytest.mark.parametrize(
    "overrides",
    [
        {"loan_id": ""},
        {"user_id": ""},
        {"isbn": None},
        {"requested_on": None},
    ],
)
def test_invalid_loan_data_is_rejected(overrides: dict[str, object]) -> None:
    """A loan record needs a loan id, a user id, an isbn and a request date."""
    with pytest.raises(InvalidLoanDataError):
        make_loan(**overrides)
