"""pytest-bdd step definitions that execute features/loan-0-create-user.feature."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import cfparse
from starlette.testclient import TestClient

from loans.domain.email import Email
from loans.domain.ports import UserRepository
from loans.domain.user import User

_FEATURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "loan-0-create-user.feature"
    )
)

scenarios(_FEATURE_PATH)

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
