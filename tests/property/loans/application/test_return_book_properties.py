"""Property tests for the return-book use case."""

from __future__ import annotations

from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from loans.application.return_book import ReturnBook
from loans.domain.events import BookReturned
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanNotActiveError, LoanStatus
from tests.unit.loans.fakes import InMemoryLoans, InMemoryPublisher

LOAN_ID = "loan-1"
USER_ID = "user-1"
ISBN = Isbn("978-0-20-163361-0")
_DATES = st.dates()
_STATUSES = st.sampled_from(list(LoanStatus))


def make_loan(requested_on, status: LoanStatus) -> Loan:
    """Build a loan in the given status with the matching due date."""
    has_due = status in (LoanStatus.ACTIVE, LoanStatus.RETURNED)
    return Loan(
        loan_id=LOAN_ID,
        user_id=USER_ID,
        isbn=ISBN,
        requested_on=requested_on,
        status=status,
        due_date=requested_on + timedelta(days=28) if has_due else None,
    )


@given(_DATES, _STATUSES)
async def test_a_non_active_return_is_refused_without_side_effects(
    requested_on, status: LoanStatus
) -> None:
    """For any date and any non-ACTIVE status, a return is refused cleanly."""
    if status is LoanStatus.ACTIVE:
        pytest.skip("ACTIVE loans are returned, not refused")
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    await store.save(make_loan(requested_on, status))

    with pytest.raises(LoanNotActiveError):
        await ReturnBook(store, publisher).execute(LOAN_ID)

    stored = await store.get(LOAN_ID)
    assert stored is not None
    assert stored.status is status
    assert publisher.events == []


@given(_DATES)
async def test_an_active_return_always_publishes_exactly_one_matching_event(requested_on) -> None:
    """For any request date (on time or overdue), one matching event is published."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    loan = make_loan(requested_on, LoanStatus.ACTIVE)
    await store.save(loan)

    updated = await ReturnBook(store, publisher).execute(LOAN_ID)

    assert updated.status is LoanStatus.RETURNED
    assert updated.due_date == loan.due_date
    assert publisher.events == [BookReturned(loan_id=LOAN_ID, user_id=USER_ID, isbn=loan.isbn)]


@given(_DATES)
async def test_returning_a_returned_loan_never_publishes_a_second_event(requested_on) -> None:
    """Once returned, further returns are refused and no extra event appears."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    await store.save(make_loan(requested_on, LoanStatus.ACTIVE))
    use_case = ReturnBook(store, publisher)
    await use_case.execute(LOAN_ID)

    with pytest.raises(LoanNotActiveError):
        await use_case.execute(LOAN_ID)

    assert len(publisher.events) == 1
