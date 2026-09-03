"""Unit tests for the reservation settlement use cases."""

from datetime import date, timedelta

import pytest

from loans.application.settle_reservation import (
    FulfillReservation,
    RejectReservation,
)
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanNotFoundError, LoanNotPendingError, LoanStatus
from tests.unit.loans.fakes import InMemoryLoans

LOAN_ID = "loan-1"


@pytest.fixture()
async def loans() -> InMemoryLoans:
    """A loan store holding one PENDING loan for a known user."""
    store = InMemoryLoans()
    await store.save(
        Loan(
            loan_id=LOAN_ID,
            user_id="user-1",
            isbn=Isbn("978-0-20-163361-0"),
            requested_on=date(2026, 9, 3),
        )
    )
    return store


async def test_fulfill_activates_pending_loan(loans: InMemoryLoans) -> None:
    """Fulfilling the reservation activates the loan with a due date."""
    updated = await FulfillReservation(loans).execute(LOAN_ID)

    assert updated.status is LoanStatus.ACTIVE
    assert updated.due_date == date(2026, 9, 3) + timedelta(days=28)
    assert (await loans.get(LOAN_ID)) is not None


async def test_reject_marks_loan_rejected(loans: InMemoryLoans) -> None:
    """Rejecting the reservation keeps the loan queryable in REJECTED."""
    updated = await RejectReservation(loans).execute(LOAN_ID)

    assert updated.status is LoanStatus.REJECTED
    assert updated.due_date is None
    assert (await loans.get(LOAN_ID)) is not None


async def test_fulfill_unknown_loan_raises(loans: InMemoryLoans) -> None:
    """Settling an id that names no loan is a lookup failure."""
    with pytest.raises(LoanNotFoundError):
        await FulfillReservation(loans).execute("missing")


async def test_reject_unknown_loan_raises(loans: InMemoryLoans) -> None:
    """Settling an id that names no loan is a lookup failure."""
    with pytest.raises(LoanNotFoundError):
        await RejectReservation(loans).execute("missing")


@pytest.mark.parametrize(
    "first, second",
    [
        (FulfillReservation, FulfillReservation),
        (FulfillReservation, RejectReservation),
        (RejectReservation, FulfillReservation),
    ],
)
async def test_a_settled_loan_cannot_be_settled_again(
    loans: InMemoryLoans, first: type, second: type
) -> None:
    """Only PENDING loans accept a reservation outcome."""
    await first(loans).execute(LOAN_ID)
    with pytest.raises(LoanNotPendingError):
        await second(loans).execute(LOAN_ID)
