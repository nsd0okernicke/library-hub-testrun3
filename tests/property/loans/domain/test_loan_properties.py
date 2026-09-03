"""Property tests for the Loan entity and reservation settlement."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from loans.application.settle_reservation import FulfillReservation, RejectReservation
from loans.domain.isbn import Isbn
from loans.domain.loan import LOAN_TERM_DAYS, Loan, LoanNotPendingError, LoanStatus
from tests.unit.loans.fakes import InMemoryLoans

_DATES = st.dates()
_ISBNS = st.from_regex(r"\d(?:-?\d){12}", fullmatch=True)


def make_loan(requested_on) -> Loan:
    """Build a PENDING loan with generated isbn and the given request date."""
    return Loan(
        loan_id="loan-1",
        user_id="user-1",
        isbn=Isbn("978-0-20-163361-0"),
        requested_on=requested_on,
    )


@given(_DATES)
def test_fulfillment_due_date_is_request_date_plus_global_term(requested_on) -> None:
    """For any request date, the due date is the request date plus the term."""
    loan = make_loan(requested_on)
    loan.fulfill()
    assert loan.status is LoanStatus.ACTIVE
    assert loan.due_date == requested_on + timedelta(days=LOAN_TERM_DAYS)


@given(_DATES)
def test_rejection_never_sets_a_due_date(requested_on) -> None:
    """A rejected loan never carries a due date, for any request date."""
    loan = make_loan(requested_on)
    loan.reject()
    assert loan.status is LoanStatus.REJECTED
    assert loan.due_date is None


@given(_DATES)
def test_return_keeps_the_due_date_set_at_fulfillment(requested_on) -> None:
    """A returned loan keeps the due date set when it was fulfilled."""
    loan = make_loan(requested_on)
    loan.fulfill()
    loan.mark_returned()
    assert loan.status is LoanStatus.RETURNED
    assert loan.due_date == requested_on + timedelta(days=LOAN_TERM_DAYS)


@given(_DATES, st.sampled_from(["fulfill", "reject"]), st.sampled_from(["fulfill", "reject"]))
def test_any_second_settlement_is_refused(requested_on, first: str, second: str) -> None:
    """Once settled by any outcome, further settlement is always refused."""
    loan = make_loan(requested_on)
    (loan.fulfill if first == "fulfill" else loan.reject)()
    with pytest.raises(LoanNotPendingError):
        (loan.fulfill if second == "fulfill" else loan.reject)()


@given(st.sampled_from(["fulfill", "reject"]))
async def test_settlement_round_trips_through_the_repository(outcome: str) -> None:
    """Settling a stored loan persists the outcome for a later read."""
    store = InMemoryLoans()
    await store.save(make_loan(date(2026, 9, 3)))
    use_case = FulfillReservation(store) if outcome == "fulfill" else RejectReservation(store)
    updated = await use_case.execute("loan-1")

    reloaded = await store.get("loan-1")
    assert reloaded is not None
    assert reloaded.status is updated.status
    assert reloaded.due_date == updated.due_date
    assert reloaded.isbn == updated.isbn
    assert reloaded.user_id == updated.user_id
