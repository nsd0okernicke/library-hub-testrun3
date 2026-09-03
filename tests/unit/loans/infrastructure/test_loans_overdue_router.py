"""Unit tests for the GET /loans/overdue HTTP route."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from starlette.testclient import TestClient

from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from loans.infrastructure.api.main import create_app
from tests.unit.loans.fakes import InMemoryLoans, InMemoryUsers

TODAY = date.today()
ISBN_A = "978-0-20-163361-0"
ISBN_B = "978-0-13-468599-1"
ISBN_C = "978-0-42-104410-0"


def make_loan(
    loan_id: str, user_id: str, isbn: str, status: LoanStatus, due_date: date | None
) -> Loan:
    """Build a loan in the given status with the given due date."""
    return Loan(
        loan_id=loan_id,
        user_id=user_id,
        isbn=Isbn(isbn),
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


def make_client() -> tuple[TestClient, InMemoryLoans]:
    """Build a TestClient around the loan app wired to fresh fakes."""
    loans = InMemoryLoans()
    return TestClient(create_app(InMemoryUsers(), loans)), loans


def test_overdue_route_returns_200_and_all_overdue_loans() -> None:
    """The list spans all users and holds exactly the overdue ACTIVE loans."""
    client, loans = make_client()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=1)),
        make_loan("l2", "user-2", ISBN_B, LoanStatus.ACTIVE, TODAY - timedelta(days=10)),
        make_loan("l3", "user-1", ISBN_C, LoanStatus.ACTIVE, TODAY + timedelta(days=5)),
        make_loan("l4", "user-1", ISBN_C, LoanStatus.RETURNED, TODAY - timedelta(days=3)),
        make_loan("l5", "user-1", ISBN_A, LoanStatus.PENDING, None),
        make_loan("l6", "user-1", ISBN_A, LoanStatus.REJECTED, None),
    )

    response = client.get("/loans/overdue")

    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, list), body
    assert [item["isbn"] for item in body] == [ISBN_B, ISBN_A]


def test_overdue_entries_carry_all_reported_fields() -> None:
    """Each entry names loan id, user id, isbn, status, due date, created_at."""
    client, loans = make_client()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=1)),
    )

    body = client.get("/loans/overdue").json()

    assert len(body) == 1
    entry = body[0]
    assert entry["loan_id"] == "l1"
    assert entry["user_id"] == "user-1"
    assert entry["isbn"] == ISBN_A
    assert entry["status"] == "ACTIVE"
    assert entry["due_date"] == (TODAY - timedelta(days=1)).isoformat()
    assert entry["created_at"]


def test_overdue_list_sorted_by_due_date_ascending() -> None:
    """Most overdue first: due date ascending across the list."""
    client, loans = make_client()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY - timedelta(days=2)),
        make_loan("l2", "user-2", ISBN_B, LoanStatus.ACTIVE, TODAY - timedelta(days=9)),
        make_loan("l3", "user-1", ISBN_C, LoanStatus.ACTIVE, TODAY - timedelta(days=5)),
    )

    body = client.get("/loans/overdue").json()

    assert [item["loan_id"] for item in body] == ["l2", "l3", "l1"]


def test_overdue_list_empty_when_nothing_overdue() -> None:
    """Without overdue loans the response body is an empty list."""
    client, loans = make_client()
    seed(
        loans,
        make_loan("l1", "user-1", ISBN_A, LoanStatus.ACTIVE, TODAY + timedelta(days=20)),
    )

    response = client.get("/loans/overdue")

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_overdue_route_not_shadowed_by_loan_id_route() -> None:
    """GET /loans/overdue must not be captured as a loan id lookup."""
    client, _ = make_client()

    response = client.get("/loans/overdue")

    assert response.status_code == 200, response.text
