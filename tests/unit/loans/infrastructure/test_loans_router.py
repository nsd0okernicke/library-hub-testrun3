"""Unit tests for the loans HTTP API (POST /loans, reservation outcomes, loan list)."""

import asyncio
from datetime import date, timedelta

import pytest
from starlette.testclient import TestClient

from loans.domain.email import Email
from loans.domain.events import BookReturned
from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from loans.domain.user import User
from loans.infrastructure.api.main import create_app
from tests.unit.loans.fakes import InMemoryLoans, InMemoryPublisher, InMemoryUsers

VALID_ISBN = "978-0-20-163361-0"


def make_client(users: InMemoryUsers, loans: InMemoryLoans) -> TestClient:
    """Build a TestClient around the loan app wired to the given fakes."""
    return TestClient(create_app(users, loans))


def seed_user(users: InMemoryUsers, user_id: str = "user-1") -> User:
    """Persist a known user and return it.

    The email derives from the user id so two seeded users never collide on
    the account identity.
    """
    user = User(user_id=user_id, name="Anna Schmidt", email=Email(f"{user_id}@example.com"))
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


# ---------------------------------------------------------------------------
# POST /loans/{loan_id}/return: ACTIVE-only return with a BookReturned event
# ---------------------------------------------------------------------------


def _active_loan_id(client: TestClient) -> str:
    """Borrow and fulfill the default isbn, returning the ACTIVE loan id."""
    loan_id = _borrow(client)
    client.post(f"/loans/{loan_id}/reservation/fulfilled")
    return loan_id


def test_return_active_loan_closes_it_and_publishes_book_returned() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    publisher = InMemoryPublisher()
    client = TestClient(create_app(users, loans, publisher))
    loan_id = _active_loan_id(client)

    response = client.post(f"/loans/{loan_id}/return")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["loan_id"] == loan_id
    assert body["user_id"] == "user-1"
    assert body["isbn"] == VALID_ISBN
    assert body["status"] == "RETURNED"
    assert body["due_date"] == (date.today() + timedelta(days=28)).isoformat()
    assert publisher.events == [
        BookReturned(loan_id=loan_id, user_id="user-1", isbn=Isbn(VALID_ISBN))
    ]


@pytest.mark.parametrize("setup", ["pending", "rejected", "returned"])
def test_returning_a_non_active_loan_returns_409_and_publishes_nothing(setup: str) -> None:
    """PENDING, REJECTED and RETURNED loans are refused with 409, status intact."""
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    publisher = InMemoryPublisher()
    client = TestClient(create_app(users, loans, publisher))
    loan_id = _borrow(client)
    expected_status = {
        "pending": "PENDING",
        "rejected": "REJECTED",
        "returned": "RETURNED",
    }[setup]
    if setup == "rejected":
        assert client.post(f"/loans/{loan_id}/reservation/rejected").status_code == 200
    elif setup == "returned":
        assert client.post(f"/loans/{loan_id}/reservation/fulfilled").status_code == 200

        async def _mark_returned() -> None:
            loan = await loans.get(loan_id)
            assert loan is not None
            loan.mark_returned()
            await loans.save(loan)

        asyncio.run(_mark_returned())

    response = client.post(f"/loans/{loan_id}/return")

    assert response.status_code == 409, response.text
    assert client.get(f"/loans/{loan_id}").json()["status"] == expected_status
    assert publisher.events == []


def test_returning_an_unknown_loan_returns_404() -> None:
    client = make_client(InMemoryUsers(), InMemoryLoans())

    assert client.post("/loans/unknown-loan-id-1/return").status_code == 404


def test_returning_after_the_due_date_closes_the_loan_without_penalty() -> None:
    """An overdue return closes exactly like an on-time one: no extra fields."""
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)
    loan_id = _active_loan_id(client)

    async def _make_overdue() -> None:
        loan = await loans.get(loan_id)
        assert loan is not None
        loan.due_date = date.today() - timedelta(days=10)
        await loans.save(loan)

    asyncio.run(_make_overdue())
    response = client.post(f"/loans/{loan_id}/return")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "RETURNED"
    assert body["due_date"] == (date.today() - timedelta(days=10)).isoformat()
    assert not (set(body) & {"penalty", "fee", "overdue"}), body


# ---------------------------------------------------------------------------
# GET /users/{user_id}/loans: paginated per-user loan list
# ---------------------------------------------------------------------------


def seed_loan(
    loans: InMemoryLoans,
    user_id: str,
    isbn: str,
    created: date,
    status: LoanStatus,
    loan_id: str,
) -> None:
    """Store a loan directly with a chosen creation date and status."""
    fulfilled = status in (LoanStatus.ACTIVE, LoanStatus.RETURNED)
    due = created + timedelta(days=28) if fulfilled else None
    asyncio.run(
        loans.save(
            Loan(
                loan_id=loan_id,
                user_id=user_id,
                isbn=Isbn(isbn),
                requested_on=created,
                status=status,
                due_date=due,
            )
        )
    )


def seed_list_users_and_loans(users: InMemoryUsers, loans: InMemoryLoans) -> None:
    """Seed user-1 with one loan per status on distinct dates, plus one for user-2."""
    seed_user(users)
    seed_loan(loans, "user-1", "978-0-20-163361-0", date(2026, 1, 4), LoanStatus.REJECTED, "L1")
    seed_loan(loans, "user-1", "978-0-13-468599-1", date(2026, 1, 5), LoanStatus.ACTIVE, "L2")
    seed_loan(loans, "user-1", "978-0-42-104410-0", date(2026, 1, 6), LoanStatus.PENDING, "L3")
    seed_loan(loans, "user-1", "978-0-67-977354-9", date(2026, 1, 7), LoanStatus.RETURNED, "L4")
    seed_user(users, user_id="user-2")
    seed_loan(loans, "user-2", "978-0-13-468599-1", date(2026, 1, 7), LoanStatus.ACTIVE, "L5")


def test_list_returns_newest_first_with_all_fields() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_list_users_and_loans(users, loans)
    client = make_client(users, loans)

    response = client.get("/users/user-1/loans")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert body["page"] == 1
    assert body["page_size"] == 20
    items = body["items"]
    assert [item["isbn"] for item in items] == [
        "978-0-67-977354-9",
        "978-0-42-104410-0",
        "978-0-13-468599-1",
        "978-0-20-163361-0",
    ]
    for item in items:
        for key in ("loan_id", "user_id", "isbn", "status", "due_date", "created_at"):
            assert key in item, key
    by_status = {item["status"]: item for item in items}
    assert by_status["ACTIVE"]["due_date"] is not None
    assert by_status["RETURNED"]["due_date"] is not None
    assert by_status["PENDING"]["due_date"] is None
    assert by_status["REJECTED"]["due_date"] is None


def test_list_excludes_other_users_loans() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_list_users_and_loans(users, loans)
    client = make_client(users, loans)

    response = client.get("/users/user-2/loans")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["isbn"] for item in body["items"]] == ["978-0-13-468599-1"]
    assert body["total"] == 1


def test_list_user_without_loans_gets_empty_list() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_user(users)
    client = make_client(users, loans)

    response = client.get("/users/user-1/loans")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_unknown_user_returns_404() -> None:
    client = make_client(InMemoryUsers(), InMemoryLoans())

    assert client.get("/users/ghost/loans").status_code == 404


def test_list_page_beyond_last_returns_empty_items_with_total_unchanged() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_list_users_and_loans(users, loans)
    client = make_client(users, loans)

    response = client.get("/users/user-1/loans?page=5&page_size=1")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 4
    assert body["page"] == 5
    assert body["page_size"] == 1


def test_list_pages_walk_the_newest_first_order() -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_list_users_and_loans(users, loans)
    client = make_client(users, loans)

    seen = [
        item["isbn"]
        for page in (1, 2, 3, 4)
        for item in client.get(f"/users/user-1/loans?page={page}&page_size=1").json()["items"]
    ]

    assert seen == [
        "978-0-67-977354-9",
        "978-0-42-104410-0",
        "978-0-13-468599-1",
        "978-0-20-163361-0",
    ]


@pytest.mark.parametrize(
    ("page", "page_size"),
    [(0, 20), (-1, 20), (1, 0), (1, -3), (1, 101)],
)
def test_list_rejects_out_of_range_pagination_with_400(page: int, page_size: int) -> None:
    users, loans = InMemoryUsers(), InMemoryLoans()
    seed_list_users_and_loans(users, loans)
    client = make_client(users, loans)

    response = client.get(f"/users/user-1/loans?page={page}&page_size={page_size}")

    assert response.status_code == 400, response.text
