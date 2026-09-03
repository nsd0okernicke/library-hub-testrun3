"""pytest-bdd step definitions for the loan-*.feature files."""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta
from typing import Any

from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import cfparse
from sqlalchemy import update
from starlette.testclient import TestClient

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.infrastructure.db.models import BookRow
from loans.domain.email import Email
from loans.domain.loan import Loan, LoanStatus
from loans.domain.ports import LoanRepository, UserRepository
from loans.domain.user import User

_FEATURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "loan-0-create-user.feature"
    )
)

_LOAN_1_FEATURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "loan-1-borrow-book.feature"
    )
)

scenarios(_FEATURE_PATH)
scenarios(_LOAN_1_FEATURE_PATH)

_PROBLEMS_BY_EMAIL = {
    'the email is "plainaddress" without an @ sign': "plainaddress",
    'the email is "@example.com" without a local part': "@example.com",
    'the email is "user@" without a domain': "user@",
}


def _post_user(context: Any, payload: dict[str, object]) -> None:
    """Record the pre-request user count and send POST /users."""
    repository: UserRepository = context.loans.repository
    context.user_count_before = asyncio.run(repository.count())
    client: TestClient = context.loans.client
    context.response = client.post("/users", json=payload)


def _seeded_user(context: Any, email: str) -> User:
    """Fetch the user stored for the email, failing loudly if absent."""
    user = asyncio.run(context.loans.repository.get_by_email(Email(email)))
    assert user is not None, f"user with email {email} not found"
    return user


@given("the users service is running")
def users_service_running(context: Any, loans: Any) -> None:
    """Wire the scenario context to the running loan service app."""
    context.loans = loans


@given(cfparse('a user with email "{email}" already exists'))
def user_already_exists(context: Any, email: str) -> None:
    """Pre-seed the account base with a user carrying this email."""
    asyncio.run(
        context.loans.repository.save(
            User(user_id=f"seed-{email}", name="Pre-seeded User", email=Email(email))
        )
    )
    context.existing_user_id = f"seed-{email}"


@when(cfparse('a user is requested with name "{name}" and email "{email}"'))
def user_requested(context: Any, name: str, email: str) -> None:
    """Send a create-user request with the given name and email."""
    _post_user(context, {"name": name, "email": email})


@when(cfparse("a user is requested where {problem}"))
def user_requested_with_problem(context: Any, problem: str) -> None:
    """Send a create-user request that violates exactly the named rule."""
    payload: dict[str, object] = {"name": "Valid Name", "email": "valid@example.com"}
    if problem == "the name is missing":
        payload.pop("name")
    elif problem == "the name is empty":
        payload["name"] = ""
    elif problem == "the email is missing":
        payload.pop("email")
    elif problem in _PROBLEMS_BY_EMAIL:
        payload["email"] = _PROBLEMS_BY_EMAIL[problem]
    else:
        raise AssertionError(f"unknown problem: {problem!r}")
    _post_user(context, payload)


@then(
    cfparse(
        'the response contains the name "{name}", the email "{email}" '
        "and a system-generated user id"
    )
)
def response_contains_user_data(context: Any, name: str, email: str) -> None:
    """Assert the response echoes the requested data plus a system user id."""
    body = context.response.json()
    assert body["name"] == name
    assert body["email"] == email
    assert body["user_id"]


@then(cfparse('a user with email "{email}" exists in the system'))
def user_exists(context: Any, email: str) -> None:
    """Assert the system now holds a user with this email."""
    assert _seeded_user(context, email) is not None


@then("the new user's user id is different from the existing user's user id")
def new_user_id_differs(context: Any) -> None:
    """Assert the created account got its own distinct user id."""
    assert context.response.json()["user_id"] != context.existing_user_id


@then(cfparse('exactly one user with email "{email}" exists in the system'))
def exactly_one_user_with_email(context: Any, email: str) -> None:
    """Assert the pre-existing user survived and no second one was added.

    User identity is the email, so at most one user can carry it; finding
    the seeded one (and only the seeded one) confirms the duplicate was
    rejected.
    """
    user = _seeded_user(context, email)
    assert user.user_id == context.existing_user_id


@then("no user was added to the system")
def no_user_added(context: Any) -> None:
    """Assert the rejected request left the account base size unchanged."""
    after = asyncio.run(context.loans.repository.count())
    assert after == context.user_count_before


# ---------------------------------------------------------------------------
# loan-1-borrow-book.feature: async borrow with out-of-band reservation
# ---------------------------------------------------------------------------


@given("the loan service is running")
def loan_service_running(context: Any, loans: Any) -> None:
    """Wire the scenario context to the running loan service app."""
    context.loans = loans


@given("the catalog service is running")
def catalog_service_running(context: Any, catalog: Any) -> None:
    """Wire the scenario context to the running catalog app."""
    context.catalog = catalog


@given(cfparse('a user with name "{name}" and email "{email}"'))
def user_created(context: Any, name: str, email: str) -> None:
    """Create the scenario's user through the users API and remember its id."""
    response = context.loans.client.post("/users", json={"name": name, "email": email})
    assert response.status_code == 201, response.text
    context.user_id = response.json()["user_id"]


@given(cfparse('a book with isbn "{isbn}" and initial stock {stock:d}'))
def book_seeded(context: Any, isbn: str, stock: int) -> None:
    """Seed the catalog with a book carrying this ISBN and stock.

    When the book was already seeded (e.g. two scenario rows name the same
    ISBN), its stock is set to the given value instead of duplicating it.
    """
    existing = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    if existing is None:
        asyncio.run(
            context.catalog.repository.save(
                Book(
                    isbn=Isbn(isbn),
                    title="Borrowed Book",
                    author="Test Author",
                    genre="Fiction",
                    available_stock=stock,
                )
            )
        )
        return

    async def _restock() -> None:
        async with context.catalog.session_factory() as session:
            await session.execute(
                update(BookRow)
                .where(BookRow.isbn == Isbn(isbn).digits)
                .values(available_stock=stock)
            )
            await session.commit()

    asyncio.run(_restock())


@given(cfparse('the user has an active loan for the book with isbn "{isbn}"'))
def user_has_active_loan(context: Any, isbn: str) -> None:
    """Give the user an already fulfilled loan for this isbn."""
    response = context.loans.client.post("/loans", json={"user_id": context.user_id, "isbn": isbn})
    assert response.status_code == 202, response.text
    loan_id = response.json()["loan_id"]
    settled = context.loans.client.post(f"/loans/{loan_id}/reservation/fulfilled")
    assert settled.status_code == 200, settled.text
    context.active_loan_ids = getattr(context, "active_loan_ids", {})
    context.active_loan_ids.setdefault(isbn, []).append(loan_id)


def _post_borrow(context: Any, user_id: str, isbn: str) -> None:
    """Record the pre-request loan count and send the borrow request."""
    repository: LoanRepository = context.loans.loan_repository
    context.loan_count_before = asyncio.run(repository.count())
    context.borrow_date = date.today()
    client: TestClient = context.loans.client
    context.response = client.post("/loans", json={"user_id": user_id, "isbn": isbn})
    if context.response.status_code == 202:
        context.loan_id = context.response.json()["loan_id"]


@when(cfparse('the user requests to borrow the book with isbn "{isbn}"'))
def borrow_requested(context: Any, isbn: str) -> None:
    """Send the scenario user a borrow request for the book."""
    _post_borrow(context, context.user_id, isbn)


@when(
    cfparse(
        'a borrow request is made for the book with isbn "{isbn}" for a user id that does not exist'
    )
)
def borrow_requested_for_unknown_user(context: Any, isbn: str) -> None:
    """Send a borrow request naming a user id that exists in no account."""
    _post_borrow(context, "no-such-user", isbn)


@when(cfparse("a borrow request is made where {problem}"))
def borrow_requested_with_problem(context: Any, problem: str) -> None:
    """Send a borrow request that violates exactly the named rule."""
    payload: dict[str, object] = {"user_id": context.user_id, "isbn": "978-0-20-163361-0"}
    if problem == "the user id is missing":
        payload.pop("user_id")
    elif problem == "the isbn is missing":
        payload.pop("isbn")
    elif problem == 'the isbn "978-0-14-103614" has 12 digits':
        payload["isbn"] = "978-0-14-103614"
    elif problem == 'the isbn "978-0-14-103614-34" has 14 digits':
        payload["isbn"] = "978-0-14-103614-34"
    elif problem == 'the isbn "978-0-14-103614-X" contains a letter':
        payload["isbn"] = "978-0-14-103614-X"
    else:
        raise AssertionError(f"unknown problem: {problem!r}")
    context.loan_count_before = asyncio.run(context.loans.loan_repository.count())
    context.response = context.loans.client.post("/loans", json=payload)


async def _settle_reservation(context: Any, isbn: str, outcome: str) -> None:
    """Play the out-of-band reservation outcome for the last borrow request.

    Filling the reservation also decrements the book's available stock in
    the catalog, the way the catalog-side reservation process does.
    """
    repository: LoanRepository = context.loans.loan_repository
    loan: Loan = await repository.get(context.loan_id)
    assert loan is not None, f"loan {context.loan_id} not found"
    assert loan.isbn.digits == Isbn(isbn).digits, "reservation named a different book"
    if outcome == "fulfilled":
        async with context.catalog.session_factory() as session:
            await session.execute(
                update(BookRow)
                .where(BookRow.isbn == Isbn(isbn).digits)
                .values(available_stock=BookRow.available_stock - 1)
            )
            await session.commit()
    context.response = context.loans.client.post(f"/loans/{context.loan_id}/reservation/{outcome}")


@when(cfparse('the reservation for the book with isbn "{isbn}" is fulfilled'))
def reservation_fulfilled(context: Any, isbn: str) -> None:
    """Fulfill the reservation: the catalog stock drops and the loan activates."""
    asyncio.run(_settle_reservation(context, isbn, "fulfilled"))


@when(cfparse('the reservation for the book with isbn "{isbn}" is rejected'))
def reservation_rejected(context: Any, isbn: str) -> None:
    """Reject the reservation: the stock stays untouched and the loan is rejected."""
    asyncio.run(_settle_reservation(context, isbn, "rejected"))


@then(
    cfparse(
        "the response contains a system-generated loan id, the user id, "
        'the isbn "{isbn}" and the status PENDING'
    )
)
def borrow_response_contains_loan(context: Any, isbn: str) -> None:
    """Assert the 202 response names the new PENDING loan for this user/isbn."""
    body = context.response.json()
    assert body["loan_id"]
    assert body["user_id"] == context.user_id
    assert body["isbn"] == isbn
    assert body["status"] == "PENDING"


async def _current_loan(context: Any) -> Loan:
    """Fetch the loan created by the last borrow request."""
    loan = await context.loans.loan_repository.get(context.loan_id)
    assert loan is not None, f"loan {context.loan_id} not found"
    return loan


@then("the loan is in status ACTIVE")
def loan_is_active(context: Any) -> None:
    """Assert the settled loan is ACTIVE."""
    loan = asyncio.run(_current_loan(context))
    assert loan.status is LoanStatus.ACTIVE, loan.status


@then("the loan is in status REJECTED")
def loan_is_rejected(context: Any) -> None:
    """Assert the settled loan is REJECTED."""
    loan = asyncio.run(_current_loan(context))
    assert loan.status is LoanStatus.REJECTED, loan.status


@then("the loan's due date is 28 days after the borrow request")
def due_date_is_28_days_after_request(context: Any) -> None:
    """Assert the due date is the request date plus the global loan term."""
    loan = asyncio.run(_current_loan(context))
    assert loan.due_date == context.borrow_date + timedelta(days=28)


@then("the loan has no due date")
def loan_has_no_due_date(context: Any) -> None:
    """Assert the rejected loan carries no due date."""
    loan = asyncio.run(_current_loan(context))
    assert loan.due_date is None


@then("the loan remains queryable in status REJECTED")
def loan_queryable_rejected(context: Any) -> None:
    """Assert GET /loans/{id} still returns the rejected loan."""
    response = context.loans.client.get(f"/loans/{context.loan_id}")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REJECTED"


@then(cfparse('the available stock of the book with isbn "{isbn}" is one less than {stock:d}'))
def stock_decreased(context: Any, isbn: str, stock: int) -> None:
    """Assert fulfilling the reservation decremented the available stock."""
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    assert book is not None
    assert book.available_stock == stock - 1


@then(cfparse('the available stock of the book with isbn "{isbn}" is unchanged at {stock:d}'))
def stock_unchanged(context: Any, isbn: str, stock: int) -> None:
    """Assert the available stock of the book is exactly the given value."""
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    assert book is not None
    assert book.available_stock == stock


@then(
    cfparse(
        'the user has an active loan for the book with isbn "{first}" '
        'and another active loan for the book with isbn "{second}"'
    )
)
def user_has_two_active_loans(context: Any, first: str, second: str) -> None:
    """Assert both named loans of the user are ACTIVE at the same time."""
    repository: LoanRepository = context.loans.loan_repository
    for loan_id in context.active_loan_ids.get(first, []):
        loan = asyncio.run(repository.get(loan_id))
        assert loan is not None and loan.status is LoanStatus.ACTIVE
    loan = asyncio.run(_current_loan(context))
    assert loan.isbn.digits == Isbn(second).digits
    assert loan.status is LoanStatus.ACTIVE


@then("no loan was created")
def no_loan_created(context: Any) -> None:
    """Assert the rejected request left the loan store size unchanged."""
    after = asyncio.run(context.loans.loan_repository.count())
    assert after == context.loan_count_before
