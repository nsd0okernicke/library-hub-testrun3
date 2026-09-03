"""Unit tests for the ViewUserLoans use case."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from loans.application.view_user_loans import ViewUserLoans
from loans.domain.email import Email
from loans.domain.exceptions import UnknownUserError
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from loans.domain.loan_list import LoanListQuery
from loans.domain.user import User
from tests.unit.loans.fakes import InMemoryLoans, InMemoryUsers

ISBNS = ["978-0-20-163361-0", "978-0-13-468599-1", "978-0-42-104410-0", "978-0-67-977354-9"]


@pytest.fixture()
async def loans() -> InMemoryLoans:
    """An in-memory loan store."""
    return InMemoryLoans()


@pytest.fixture()
async def users() -> InMemoryUsers:
    """An account base with a single user-1 account."""
    base = InMemoryUsers()
    await base.save(User(user_id="user-1", name="Anna Schmidt", email=Email("a@example.com")))
    return base


def add_loan(
    user_id: str,
    isbn: str,
    created: date,
    status: LoanStatus = LoanStatus.PENDING,
) -> Loan:
    """Store a loan in the given status with the given creation date.

    ACTIVE and RETURNED loans carry the due date the fulfillment would
    have set: creation date plus the global loan term.
    """
    fulfilled = status in (LoanStatus.ACTIVE, LoanStatus.RETURNED)
    due = created + timedelta(days=28) if fulfilled else None
    return Loan(
        loan_id=f"loan-{user_id}-{Isbn(isbn).digits}-{created.isoformat()}",
        user_id=user_id,
        isbn=Isbn(isbn),
        requested_on=created,
        status=status,
        due_date=due,
    )


async def seed_standard_set(users: InMemoryUsers, loans: InMemoryLoans) -> None:
    """Give user-1 one loan per status with distinct creation dates."""
    statuses = [
        (ISBNS[0], LoanStatus.REJECTED, date(2026, 1, 4)),
        (ISBNS[1], LoanStatus.ACTIVE, date(2026, 1, 5)),
        (ISBNS[2], LoanStatus.PENDING, date(2026, 1, 6)),
        (ISBNS[3], LoanStatus.RETURNED, date(2026, 1, 7)),
    ]
    for isbn, status, created in statuses:
        await loans.save(add_loan("user-1", isbn, created, status))


async def run(users: InMemoryUsers, loans: InMemoryLoans, **kwargs: object):
    """Run the use case against the fakes with the given query fields."""
    return await ViewUserLoans(users, loans).execute(LoanListQuery(user_id="user-1", **kwargs))


async def test_unknown_user_id_raises(users: InMemoryUsers, loans: InMemoryLoans) -> None:
    """A user id naming no account is a 404 in the API layer."""
    with pytest.raises(UnknownUserError):
        await ViewUserLoans(users, loans).execute(LoanListQuery(user_id="ghost"))


async def test_loans_are_listed_newest_first_in_all_statuses(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """All four statuses appear, sorted by creation date descending."""
    await seed_standard_set(users, loans)

    result = await run(users, loans)

    assert [loan.isbn.value for loan in result.items] == list(reversed(ISBNS))
    assert result.total == 4
    assert result.page == 1
    assert result.page_size == 20


async def test_only_the_requested_users_loans_are_returned(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """Other users' loans never leak into the list."""
    await seed_standard_set(users, loans)
    await users.save(User(user_id="user-2", name="Ben Meyer", email=Email("b@example.com")))
    await loans.save(add_loan("user-2", ISBNS[1], date(2026, 1, 7), LoanStatus.ACTIVE))

    result = await run(users, loans)

    assert [loan.user_id for loan in result.items] == ["user-1"] * 4
    assert result.total == 4


async def test_user_without_loans_gets_an_empty_list_with_total_zero(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """An existing account without loans yields an empty page, total 0."""
    result = await run(users, loans)

    assert result.items == []
    assert result.total == 0


async def test_page_beyond_the_last_returns_no_loans_with_total_unchanged(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """A page past the end is empty but still reports the full total."""
    await seed_standard_set(users, loans)

    result = await run(users, loans, page=5, page_size=1)

    assert result.items == []
    assert result.total == 4
    assert result.page == 5
    assert result.page_size == 1


async def test_page_size_one_walks_the_sorted_list(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """Single-item pages walk the newest-first order one loan at a time."""
    await seed_standard_set(users, loans)

    seen: list[str] = []
    for page in range(1, 5):
        result = await run(users, loans, page=page, page_size=1)
        seen.extend(loan.isbn.value for loan in result.items)

    assert seen == list(reversed(ISBNS))


async def test_larger_page_size_slicing(users: InMemoryUsers, loans: InMemoryLoans) -> None:
    """A page of two walks further into the newest-first order."""
    await seed_standard_set(users, loans)

    result = await run(users, loans, page=2, page_size=2)

    assert [loan.isbn.value for loan in result.items] == [ISBNS[1], ISBNS[0]]
    assert result.total == 4
    assert result.page == 2
    assert result.page_size == 2


async def test_active_and_returned_keep_their_due_dates(
    users: InMemoryUsers, loans: InMemoryLoans
) -> None:
    """Fulfilled loans keep their due date; PENDING and REJECTED have none."""
    await seed_standard_set(users, loans)

    result = await run(users, loans)
    by_status = {loan.status: loan for loan in result.items}

    assert by_status[LoanStatus.ACTIVE].due_date == date(2026, 1, 5) + timedelta(days=28)
    assert by_status[LoanStatus.RETURNED].due_date == date(2026, 1, 7) + timedelta(days=28)
    assert by_status[LoanStatus.PENDING].due_date is None
    assert by_status[LoanStatus.REJECTED].due_date is None
