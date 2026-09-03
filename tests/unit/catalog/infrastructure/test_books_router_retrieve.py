"""Unit tests for the catalog HTTP API (GET /books/{isbn}) with a fake repository."""

from __future__ import annotations

import asyncio

from starlette.testclient import TestClient

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository
from catalog.infrastructure.api.main import create_app
from tests.unit.catalog.fakes import InMemoryBooks


def make_client(repo: BookRepository) -> TestClient:
    """Build a TestClient around the catalog app wired to the given repo."""
    return TestClient(create_app(repo))


async def seed(repo: InMemoryBooks) -> None:
    """Store the scenario books in the fake repository."""
    await repo.save(
        Book(
            isbn=Isbn("978-0-14-103614-3"),
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            genre="Fiction",
            available_stock=5,
            description="A jazz-age novel about money",
        )
    )
    await repo.save(
        Book(
            isbn=Isbn("978-0-553-21316-7"),
            title="Brave New World",
            author="Aldous Huxley",
            genre="Dystopian",
            available_stock=2,
        )
    )


def test_retrieve_existing_book_returns_200_with_full_metadata() -> None:
    """An existing book is returned with its full metadata and stock."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/978-0-14-103614-3")

    assert response.status_code == 200
    body = response.json()
    assert body["isbn"] == "978-0-14-103614-3"
    assert body["title"] == "The Great Gatsby"
    assert body["author"] == "F. Scott Fitzgerald"
    assert body["genre"] == "Fiction"
    assert body["description"] == "A jazz-age novel about money"
    assert body["available_stock"] == 5


def test_retrieve_book_without_description_returns_empty_string() -> None:
    """A book created without a description is returned with an empty one."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/978-0-553-21316-7")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Brave New World"
    assert body["author"] == "Aldous Huxley"
    assert body["genre"] == "Dystopian"
    assert body["description"] == ""
    assert body["available_stock"] == 2


def test_retrieve_missing_book_returns_404() -> None:
    """A book that does not exist is rejected with 404 Not Found."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/978-0-20-163361-0")

    assert response.status_code == 404


def test_retrieve_invalid_isbn_returns_400() -> None:
    """A request with an invalid ISBN format is rejected with 400 Bad Request."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for isbn in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        assert client.get(f"/books/{isbn}").status_code == 400, isbn
