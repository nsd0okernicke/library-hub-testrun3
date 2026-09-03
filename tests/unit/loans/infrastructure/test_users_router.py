"""Unit tests for the loans HTTP API (POST /users) with a fake repository."""

import pytest
from starlette.testclient import TestClient

from loans.domain.ports import UserRepository
from loans.infrastructure.api.main import create_app
from tests.unit.loans.fakes import InMemoryUsers


def make_client(repo: UserRepository) -> TestClient:
    """Build a TestClient around the loan app wired to the given repo."""
    return TestClient(create_app(repo))


def test_create_user_returns_201_and_user() -> None:
    repo = InMemoryUsers()
    client = make_client(repo)

    response = client.post(
        "/users", json={"name": "Anna Schmidt", "email": "anna.schmidt@example.com"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Anna Schmidt"
    assert body["email"] == "anna.schmidt@example.com"
    assert body["user_id"]
    assert len(repo.users) == 1


def test_two_creations_get_different_user_ids() -> None:
    repo = InMemoryUsers()
    client = make_client(repo)

    client.post("/users", json={"name": "Anna Schmidt", "email": "anna.schmidt@example.com"})
    response = client.post(
        "/users", json={"name": "Ben Mueller", "email": "ben.mueller@example.com"}
    )

    assert response.status_code == 201
    assert response.json()["user_id"] != list(repo.users.values())[0].user_id


def test_duplicate_email_returns_409() -> None:
    repo = InMemoryUsers()
    client = make_client(repo)
    payload = {"name": "Anna Schmidt", "email": "anna.schmidt@example.com"}

    assert client.post("/users", json=payload).status_code == 201
    response = client.post("/users", json={"name": "Anna Reiter", "email": payload["email"]})

    assert response.status_code == 409
    assert len(repo.users) == 1


def test_duplicate_email_is_rejected_regardless_of_name() -> None:
    repo = InMemoryUsers()
    client = make_client(repo)
    client.post("/users", json={"name": "Anna Schmidt", "email": "anna.schmidt@example.com"})

    response = client.post(
        "/users", json={"name": "Someone Else", "email": "anna.schmidt@example.com"}
    )

    assert response.status_code == 409
    assert len(repo.users) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "anna.schmidt@example.com"},
        {"name": "Anna Schmidt"},
        {"name": "", "email": "anna.schmidt@example.com"},
        {"name": "Anna Schmidt", "email": "plainaddress"},
        {"name": "Anna Schmidt", "email": "@example.com"},
        {"name": "Anna Schmidt", "email": "user@"},
    ],
)
def test_invalid_request_returns_400_and_adds_no_user(payload: dict[str, str]) -> None:
    repo = InMemoryUsers()
    client = make_client(repo)

    response = client.post("/users", json=payload)

    assert response.status_code == 400, response.text
    assert len(repo.users) == 0
