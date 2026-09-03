"""Unit tests for the ViewOverdueLoans use case."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from loans.application.view_overdue_loans import ViewOverdueLoans
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from tests.unit.loans.fakes import InMemoryLoans

TODAY = date(2026, 9, 3)
ISBN_A = Isbn("978-0-20-163361-0")
ISBN_B = Isbn("978-0-13-468599-1")
ISBN_C = Isbn("978-0-42-104410-0")


def make_loan(
    loan_id: str, user_id: str, isbn: Isbn, status: LoanStatus, due_date: date | None
) -> Loan:
    """Build a loan in the given status with the given due date."""
    return Loan(
        loan_id=loan_id,
        user_id=user_id,
        isbn=isbn,
        requested_on=TODAY - timedelta(days=28),
        status=status,
        due_date=due_date,
    )


def seed(loans: InMemoryLoans, *to_save: Loan) -> None:
    """Persist several loan records into the fake repository."""

    async def save_all() -> None:
        for loan in to_save:
            await loans.save(loan)

    asyncio.run(save_all())


def run_case(loans: InMemoryLoans) -> list[Loan]:
    """Execute the use case synchronously with today's date as the current day."""
    use_case = ViewOverdueLoans(loans, today=lambda: TODAY)
    return asyncio.run(use_case.execute())


def test_active_loan_past_due_is_listed() -> None:
    """An ACTIVE loan whose due date has passed appears in the list."""
    loans = InMemoryLoans()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=1)),
    )

    result = run_case(loans)
    assert [entry.loan_id for entry in result] == ["l1"]


def test_only_active_loans_past_due_are_listed() -> None:
    """Non-overdue and non-ACTIVE loans never appear in the list."""
    loans = InMemoryLoans()
    seeded = [
        make_loan("overdue", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=3)),
        make_loan("not-yet", "user-1", ISBN_B, LoanStatus.ACTIVE, TODAY + timedelta(days=5)),
        make_loan("returned", "user-1", ISBN_C, LoanStatus.RETURNED, TODAY - timedelta(days=3)),
        make_loan("pending", "user-1", Isbn("978-0-67-977354-9"), LoanStatus.PENDING, None),
        make_loan("rejected", "user-1", Isbn("978-0-55-338211-6"), LoanStatus.REJECTED, None),
    ]
    seed(loans, *seeded)

    result = run_case(loans)
    assert [entry.loan_id for entry in result] == ["overdue"]


def test_list_spans_all_users() -> None:
    """The list is an administrative view, not filtered to a single user."""
    loans = InMemoryLoans()
    seeded = [
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=2)),
        make_loan("l2", "user-2", ISBN_B, LoanStatus.ACTIVE, TODAY - timedelta(days=9)),
    ]
    seed(loans, *seeded)

    result = run_case(loans)
    assert {entry.user_id for entry in result} == {"user-1", "user-2"}


def test_list_is_sorted_by_due_date_ascending() -> None:
    """Most overdue first: the list is sorted by due date ascending."""
    loans = InMemoryLoans()
    seeded = [
        make_loan("two-days", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=2)),
        make_loan("nine-days", "user-2", ISBN_B, LoanStatus.ACTIVE, TODAY - timedelta(days=9)),
        make_loan("five-days", "user-1", ISBN_C, LoanStatus.ACTIVE, TODAY - timedelta(days=5)),
    ]
    seed(loans, *seeded)

    result = run_case(loans)
    assert [entry.loan_id for entry in result] == ["nine-days", "five-days", "two-days"]


def test_equal_due_dates_break_ties_by_loan_id() -> None:
    """Loans sharing a due date are ordered by loan id for determinism."""
    loans = InMemoryLoans()
    seeded = [
        make_loan("b", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=4)),
        make_loan("a", "user-2", ISBN_B, LoanStatus.ACTIVE, TODAY - timedelta(days=4)),
    ]
    seed(loans, *seeded)

    result = run_case(loans)
    assert [entry.loan_id for entry in result] == ["a", "b"]


def test_empty_when_no_overdue_loans() -> None:
    """Without overdue loans the list is empty."""
    loans = InMemoryLoans()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY + timedelta(days=20)),
    )

    result = run_case(loans)
    assert result == []
