"""Unit tests for the loans HTTP API (POST /loans and reservation outcomes)."""

import asyncio
from datetime import date, timedelta

import pytest
from starlette.testclient import TestClient

from loans.domain.email import Email
from loans.domain.user import User
from loans.infrastructure.api.main import create_app
from tests.unit.loans.fakes import InMemoryLoans, InMemoryUsers

VALID_ISBN = "978-0-20-163361-0"


def make_client(users: InMemoryUsers, loans: InMemoryLoans) -> TestClient:
    """Build a TestClient around the loan app wired to the given fakes."""
    return TestClient(create_app(users, loans))


def seed_user(users: InMemoryUsers, user_id: str = "user-1") -> User:
    """Persist a known user and return it."""
    user = User(user_id=user_id, name="Anna Schmidt", email=Email("a@example.com"))
    asyncio.run(users.save(user))
    return user


def test_borrow_returns_202_and_pending_loan() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)

    response = client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN})

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["user_id"] == "user-1"
    assert body["isbn"] == VALID_ISBN
    assert body["loan_id"]
    assert len(loans.loans) == 1


def test_two_borrows_get_different_loan_ids() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    payload = {"user_id": "user-1", "isbn": VALID_ISBN}

    first = client.post("/loans", json=payload).json()
    second = client.post("/loans", json=payload).json()

    assert first["loan_id"] != second["loan_id"]
    assert len(loans.loans) == 2


def test_borrow_for_unknown_user_returns_404() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    client = make_client(users, loans)

    response = client.post("/loans", json={"user_id": "ghost", "isbn": VALID_ISBN})

    assert response.status_code == 404, response.text
    assert len(loans.loans) == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"user_id": "user-1"},
        {"user_id": "user-1", "isbn": ""},
        {"user_id": "", "isbn": VALID_ISBN},
        {"user_id": "user-1", "isbn": "978-0-14-103614"},  # 12 digits
        {"user_id": "user-1", "isbn": "978-0-14-103614-34"},  # 14 digits
        {"user_id": "user-1", "isbn": "978-0-14-103614-X"},  # letter
    ],
)
def test_borrow_with_invalid_data_returns_400(payload: dict[str, str]) -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)

    response = client.post("/loans", json=payload)

    assert response.status_code == 400, response.text
    assert len(loans.loans) == 0


def test_get_loan_returns_200_with_status_and_dates() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN}).json()[
        "loan_id"
    ]

    response = client.get(f"/loans/{loan_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["loan_id"] == loan_id
    assert body["status"] == "PENDING"
    assert body["due_date"] is None


def test_get_missing_loan_returns_404() -> None:
    client = make_client(InMemoryUsers(), InMemoryLoans())

    assert client.get("/loans/missing").status_code == 404


def _borrow(client: TestClient) -> str:
    """Borrow the default isbn and return the new loan id."""
    return client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN}).json()["loan_id"]


def test_get_active_loan_returns_status_and_due_date() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = _borrow(client)
    client.post(f"/loans/{loan_id}/reservation/fulfilled")

    response = client.get(f"/loans/{loan_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["due_date"] == (date.today() + timedelta(days=28)).isoformat()


def test_get_returned_loan_returns_returned_with_kept_due_date() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = _borrow(client)
    client.post(f"/loans/{loan_id}/reservation/fulfilled")

    async def _return_loan() -> None:
        loan = await loans.get(loan_id)
        assert loan is not None
        loan.mark_returned()
        await loans.save(loan)

    asyncio.run(_return_loan())
    response = client.get(f"/loans/{loan_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "RETURNED"
    assert body["due_date"] == (date.today() + timedelta(days=28)).isoformat()


def test_fulfill_reservation_activates_loan_with_due_date() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN}).json()[
        "loan_id"
    ]
    today = date.today()

    response = client.post(f"/loans/{loan_id}/reservation/fulfilled")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["due_date"] == (today + timedelta(days=28)).isoformat()


def test_reject_reservation_marks_loan_rejected() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN}).json()[
        "loan_id"
    ]

    response = client.post(f"/loans/{loan_id}/reservation/rejected")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["due_date"] is None


@pytest.mark.parametrize("outcome", ["fulfilled", "rejected"])
def test_settling_missing_loan_returns_404(outcome: str) -> None:
    client = make_client(InMemoryUsers(), InMemoryLoans())

    assert client.post(f"/loans/missing/reservation/{outcome}").status_code == 404


def test_settling_a_settled_loan_returns_409() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = client.post("/loans", json={"user_id": "user-1", "isbn": VALID_ISBN}).json()[
        "loan_id"
    ]
    assert client.post(f"/loans/{loan_id}/reservation/rejected").status_code == 200

    assert client.post(f"/loans/{loan_id}/reservation/fulfilled").status_code == 409
