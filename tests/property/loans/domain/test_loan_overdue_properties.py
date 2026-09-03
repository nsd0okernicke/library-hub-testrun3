"""Property tests for the Loan.is_overdue domain rule."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus

_DATES = st.dates()


def make_loan(status: LoanStatus, due_date: date | None) -> Loan:
    """Build a loan in the given status with the given due date."""
    return Loan(
        loan_id="loan-1",
        user_id="user-1",
        isbn=Isbn("978-0-20-163361-0"),
        requested_on=date(2020, 1, 1),
        status=status,
        due_date=due_date,
    )


@given(_DATES, st.none() | _DATES)
def test_overdue_is_exactly_active_with_due_date_strictly_before(
    today: date, due_date: date | None
) -> None:
    """For any day and due date, the overdue rule is the exact definition."""
    expected = (
        due_date is not None and due_date < today
    )  # the status conjunct is checked by the parametrized case below
    active = make_loan(LoanStatus.ACTIVE, due_date)
    assert active.is_overdue(today) is expected


@given(_DATES, st.none() | _DATES, st.sampled_from(LoanStatus))
def test_overdue_never_outside_active(
    today: date, due_date: date | None, status: LoanStatus
) -> None:
    """No loan in a non-ACTIVE status is ever overdue, for any due date."""
    if status is LoanStatus.ACTIVE:
        return  # the ACTIVE case is covered by the definition property
    loan = make_loan(status, due_date)
    assert loan.is_overdue(today) is False


@given(_DATES)
def test_overdue_is_monotonic_in_time(today: date) -> None:
    """A loan overdue on a day stays overdue on every later day."""
    loan = make_loan(LoanStatus.ACTIVE, today - timedelta(days=30))
    assert loan.is_overdue(today)
    for offset in range(0, 5):
        assert loan.is_overdue(today + timedelta(days=offset))


@given(_DATES)
def test_due_today_is_the_not_overdue_boundary(today: date) -> None:
    """A loan due exactly on the current day is not overdue yet."""
    loan = make_loan(LoanStatus.ACTIVE, today)
    assert loan.is_overdue(today) is False
    assert loan.is_overdue(today + timedelta(days=1)) is True
