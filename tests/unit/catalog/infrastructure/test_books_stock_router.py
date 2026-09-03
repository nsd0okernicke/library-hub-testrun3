"""Unit tests for POST /books/{isbn}/stock with a fake repository."""

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
    """Store the scenario book in the fake repository."""
    await repo.save(
        Book(
            isbn=Isbn("978-0-14-103614-3"),
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            genre="Fiction",
            available_stock=5,
        )
    )


def test_stock_increase_of_existing_book_returns_200() -> None:
    """A valid stock increase succeeds and returns the updated book."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.post("/books/978-0-14-103614-3/stock", json={"copies": 3})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["isbn"] == "978-0-14-103614-3"
    assert body["title"] == "The Great Gatsby"
    assert body["author"] == "F. Scott Fitzgerald"
    assert body["genre"] == "Fiction"
    assert body["available_stock"] == 8


def test_stock_increase_is_persisted() -> None:
    """The stock increase is stored, not just reported in the response."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    client.post("/books/978-0-14-103614-3/stock", json={"copies": 4})

    book = asyncio.run(repo.get_by_isbn(Isbn("978-0-14-103614-3")))
    assert book is not None
    assert book.available_stock == 9


def test_stock_increase_of_missing_book_returns_404() -> None:
    """A stock increase for an unknown ISBN is rejected with 404 Not Found."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for isbn in ("978-0-20-163361-0", "978-0-13-468599-1"):
        response = client.post(f"/books/{isbn}/stock", json={"copies": 2})
        assert response.status_code == 404, (isbn, response.text)
    assert asyncio.run(repo.get_by_isbn(Isbn(isbn))) is None


def test_stock_increase_with_invalid_isbn_returns_400() -> None:
    """A request with an invalid ISBN format is rejected with 400 Bad Request."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for isbn in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        response = client.post(f"/books/{isbn}/stock", json={"copies": 2})
        assert response.status_code == 400, (isbn, response.text)


def test_stock_increase_creates_no_book() -> None:
    """A rejected request leaves the catalog contents unchanged."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    client.post("/books/978-0-14-103614/stock", json={"copies": 2})

    assert asyncio.run(repo.count()) == 1


def test_stock_increase_with_non_positive_copies_returns_400() -> None:
    """Zero and negative copy counts are rejected with 400 Bad Request."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for copies in (0, -3):
        response = client.post("/books/978-0-14-103614-3/stock", json={"copies": copies})
        assert response.status_code == 400, (copies, response.text)
    book = asyncio.run(repo.get_by_isbn(Isbn("978-0-14-103614-3")))
    assert book is not None
    assert book.available_stock == 5


def test_stock_increase_with_missing_copies_returns_400() -> None:
    """A payload without a copy count is rejected with 400, not 422."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.post("/books/978-0-14-103614-3/stock", json={})

    assert response.status_code == 400, response.text
