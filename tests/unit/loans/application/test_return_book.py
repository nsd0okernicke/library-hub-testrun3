"""Unit tests for the return-book use case."""

from datetime import date

import pytest

from loans.application.return_book import ReturnBook
from loans.domain.events import BookReturned
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanNotActiveError, LoanNotFoundError, LoanStatus
from tests.unit.loans.fakes import InMemoryLoans, InMemoryPublisher

LOAN_ID = "loan-1"
ISBN = Isbn("978-0-20-163361-0")


async def store_loan(store: InMemoryLoans, status: LoanStatus) -> None:
    """Save the known loan in the given status with the matching due date."""
    has_due = status in (LoanStatus.ACTIVE, LoanStatus.RETURNED)
    await store.save(
        Loan(
            loan_id=LOAN_ID,
            user_id="user-1",
            isbn=ISBN,
            requested_on=date(2026, 9, 3),
            status=status,
            due_date=date(2026, 10, 1) if has_due else None,
        )
    )


@pytest.mark.parametrize("status", [LoanStatus.PENDING, LoanStatus.REJECTED, LoanStatus.RETURNED])
async def test_returning_a_non_active_loan_is_refused_without_side_effects(
    status: LoanStatus,
) -> None:
    """A loan that is not ACTIVE is not returned, saved or announced."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    await store_loan(store, status)

    with pytest.raises(LoanNotActiveError):
        await ReturnBook(store, publisher).execute(LOAN_ID)

    stored = await store.get(LOAN_ID)
    assert stored is not None
    assert stored.status is status
    assert publisher.events == []


async def test_returning_an_active_loan_publishes_book_returned() -> None:
    """Returning an ACTIVE loan closes it and publishes the event once."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    await store_loan(store, LoanStatus.ACTIVE)

    updated = await ReturnBook(store, publisher).execute(LOAN_ID)

    assert updated.status is LoanStatus.RETURNED
    stored = await store.get(LOAN_ID)
    assert stored is not None and stored.status is LoanStatus.RETURNED
    assert publisher.events == [BookReturned(loan_id=LOAN_ID, user_id="user-1", isbn=ISBN)]


async def test_returning_an_overdue_active_loan_closes_it_the_same_way() -> None:
    """A due date in the past changes nothing: the loan closes like an on-time one."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()
    await store.save(
        Loan(
            loan_id=LOAN_ID,
            user_id="user-1",
            isbn=ISBN,
            requested_on=date(2026, 7, 1),
            status=LoanStatus.ACTIVE,
            due_date=date(2026, 7, 29),  # in the past
        )
    )

    updated = await ReturnBook(store, publisher).execute(LOAN_ID)

    assert updated.status is LoanStatus.RETURNED
    assert updated.due_date == date(2026, 7, 29)  # kept, untouched
    assert len(publisher.events) == 1


async def test_returning_an_unknown_loan_is_a_lookup_failure() -> None:
    """A loan id that names no stored loan is a lookup failure, with no event."""
    store, publisher = InMemoryLoans(), InMemoryPublisher()

    with pytest.raises(LoanNotFoundError):
        await ReturnBook(store, publisher).execute("missing")

    assert publisher.events == []
