"""Unit tests for GET /books/{isbn}/availability with a fake repository."""

from __future__ import annotations

import asyncio

from starlette.testclient import TestClient

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.infrastructure.api.main import create_app
from tests.unit.catalog.fakes import InMemoryBooks


def make_client(repo: InMemoryBooks) -> TestClient:
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
        )
    )
    await repo.save(
        Book(
            isbn=Isbn("978-0-06-112008-4"),
            title="1984",
            author="George Orwell",
            genre="Dystopian",
            available_stock=0,
        )
    )


def test_availability_of_existing_book_returns_200() -> None:
    """An existing book is returned with its current available stock."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/978-0-14-103614-3/availability")

    assert response.status_code == 200
    assert response.json() == {"isbn": "978-0-14-103614-3", "available_count": 5}


def test_availability_response_contains_only_isbn_and_available_count() -> None:
    """The response carries no title, author, genre or description."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    body = client.get("/books/978-0-14-103614-3/availability").json()

    assert set(body) == {"isbn", "available_count"}


def test_availability_of_out_of_stock_book_reports_zero() -> None:
    """An out-of-stock book is reported with an available count of zero."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/978-0-06-112008-4/availability")

    assert response.status_code == 200
    assert response.json() == {"isbn": "978-0-06-112008-4", "available_count": 0}


def test_availability_of_missing_book_returns_404() -> None:
    """A book that does not exist is rejected with 404 Not Found."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for isbn in ("978-0-20-163361-0", "978-0-13-468599-1"):
        assert client.get(f"/books/{isbn}/availability").status_code == 404, isbn


def test_availability_invalid_isbn_returns_400() -> None:
    """A request with an invalid ISBN format is rejected with 400 Bad Request."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for isbn in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        assert client.get(f"/books/{isbn}/availability").status_code == 400, isbn
