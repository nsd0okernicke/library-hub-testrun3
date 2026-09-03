"""Property-based tests for the ViewUserLoans use case."""

from __future__ import annotations

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from loans.application.view_user_loans import ViewUserLoans
from loans.domain.email import Email
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from loans.domain.loan_list import LoanListQuery
from loans.domain.user import User
from tests.unit.loans.fakes import InMemoryLoans, InMemoryUsers

STATUSES = list(LoanStatus)


def loan_strategy(user_id: str) -> st.SearchStrategy[Loan]:
    """Generate loans with colliding creation dates to stress the tie order."""
    return st.builds(
        Loan,
        loan_id=st.uuids().map(str),
        user_id=st.just(user_id),
        isbn=st.integers(0, 10**8 - 1).map(lambda n: Isbn(f"978-0-1{str(n).zfill(8)}")),
        requested_on=st.dates(date(2026, 1, 1), date(2026, 1, 10)),
        status=st.sampled_from(STATUSES),
        due_date=st.just(None),
    )


async def build(user_loans: list[Loan], other_loans: list[Loan]):
    """Store the loans and the user-1 account in the in-memory fakes."""
    users = InMemoryUsers()
    loans = InMemoryLoans()
    await users.save(User(user_id="user-1", name="Anna", email=Email("a@example.com")))
    await users.save(User(user_id="user-2", name="Ben", email=Email("b@example.com")))
    for loan in [*user_loans, *other_loans]:
        await loans.save(loan)
    return users, loans


def newest_first(loan_list: list[Loan]) -> list[Loan]:
    """Reference ordering: created (requested_on) desc, ties by loan id asc."""
    ordered = sorted(loan_list, key=lambda loan: loan.loan_id)
    ordered.sort(key=lambda loan: loan.requested_on, reverse=True)
    return ordered


@st.composite
def paged_query(draw: st.DrawFn) -> dict[str, int]:
    """Generate a valid page and page size for a list of at most 25 loans."""
    return {
        "page": draw(st.integers(1, 30)),
        "page_size": draw(st.integers(1, 100)),
    }


@settings(max_examples=40)
@given(
    user_loans=st.lists(loan_strategy("user-1"), max_size=25),
    other_loans=st.lists(loan_strategy("user-2"), max_size=5),
    query=paged_query(),
)
async def test_total_counts_every_loan_of_the_user(
    user_loans: list[Loan], other_loans: list[Loan], query: dict[str, int]
) -> None:
    """The total counts every loan of the user, never other users' loans."""
    users, loans = await build(user_loans, other_loans)
    result = await ViewUserLoans(users, loans).execute(LoanListQuery(user_id="user-1", **query))

    assert result.total == len(user_loans)


@settings(max_examples=40)
@given(
    user_loans=st.lists(loan_strategy("user-1"), max_size=25),
    other_loans=st.lists(loan_strategy("user-2"), max_size=5),
    query=paged_query(),
)
async def test_page_is_the_newest_first_list_sliced(
    user_loans: list[Loan], other_loans: list[Loan], query: dict[str, int]
) -> None:
    """The page is the newest-first list of the user sliced at the offset."""
    users, loans = await build(user_loans, other_loans)
    result = await ViewUserLoans(users, loans).execute(LoanListQuery(user_id="user-1", **query))

    ordered = newest_first(user_loans)
    start = (query["page"] - 1) * query["page_size"]
    assert [loan.loan_id for loan in result.items] == [
        loan.loan_id for loan in ordered[start : start + query["page_size"]]
    ]
    assert len(result.items) <= query["page_size"]


@settings(max_examples=15)
@given(user_loans=st.lists(loan_strategy("user-1"), max_size=15))
async def test_all_pages_reassemble_the_full_list(user_loans: list[Loan]) -> None:
    """Walking every page with size 1 yields the full newest-first order."""
    users, loans = await build(user_loans, [])
    use_case = ViewUserLoans(users, loans)

    seen: list[str] = []
    for page in range(1, len(user_loans) + 2):  # last page + one beyond
        result = await use_case.execute(LoanListQuery(user_id="user-1", page=page, page_size=1))
        seen.extend(loan.loan_id for loan in result.items)

    assert seen == [loan.loan_id for loan in newest_first(user_loans)]


@settings(max_examples=15)
@given(user_loans=st.lists(loan_strategy("user-1"), max_size=15))
async def test_page_beyond_the_last_is_empty_with_total_unchanged(
    user_loans: list[Loan],
) -> None:
    """A page past the end returns no loans but keeps the full total."""
    users, loans = await build(user_loans, [])
    result = await ViewUserLoans(users, loans).execute(
        LoanListQuery(user_id="user-1", page=len(user_loans) + 2, page_size=3)
    )

    assert result.items == []
    assert result.total == len(user_loans)


@settings(max_examples=10)
@given(
    user_loans=st.lists(loan_strategy("user-1"), max_size=10),
    query=paged_query(),
)
async def test_listing_is_idempotent(user_loans: list[Loan], query: dict[str, int]) -> None:
    """The same query on the same data yields the same result twice."""
    users, loans = await build(user_loans, [])
    use_case = ViewUserLoans(users, loans)
    first = await use_case.execute(LoanListQuery(user_id="user-1", **query))
    second = await use_case.execute(LoanListQuery(user_id="user-1", **query))

    assert [loan.loan_id for loan in first.items] == [loan.loan_id for loan in second.items]
    assert first.total == second.total
