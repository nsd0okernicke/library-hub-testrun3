"""Unit tests for the catalog HTTP search endpoint with a fake repository."""

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
    for isbn, title, author, genre in (
        ("978-0-441-17271-9", "Dune", "Frank Herbert", "Science Fiction"),
        ("978-0-201-48567-7", "Refactoring", "Martin Fowler", "Craft"),
        ("978-0-547-92822-7", "The Hobbit", "J.R.R. Tolkien", "Fantasy"),
    ):
        await repo.save(
            Book(isbn=Isbn(isbn), title=title, author=author, genre=genre, available_stock=1)
        )


def test_search_without_filters_returns_all_books_with_pagination_metadata() -> None:
    """A bare search returns every book, the total, and the default paging."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/search")

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Dune", "Refactoring", "The Hobbit"]
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_search_result_items_carry_full_metadata_like_retrieval() -> None:
    """Each result entry has the same shape as single-book retrieval."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    item = client.get("/books/search", params={"title": "dune"}).json()["items"][0]

    assert item == {
        "isbn": "978-0-441-17271-9",
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "Science Fiction",
        "description": "",
        "available_stock": 1,
    }


def test_search_accepts_filters_and_pagination_parameters() -> None:
    """Filters and page parameters narrow and page the result set."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/search", params={"author": "tolkien", "page": 1, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["The Hobbit"]
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 1


def test_search_reports_the_requested_page_beyond_the_last() -> None:
    """A page past the end is empty but still reports page, size and total."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/search", params={"page": 4, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3
    assert body["page"] == 4
    assert body["page_size"] == 1


def test_search_with_max_page_size_is_accepted() -> None:
    """A page size of 100 is accepted and reported unchanged."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    response = client.get("/books/search", params={"page": 1, "page_size": 100})

    assert response.status_code == 200
    body = response.json()
    assert body["page_size"] == 100
    assert body["total"] == 3


def test_search_with_invalid_page_or_page_size_is_rejected_with_400() -> None:
    """Page or page size outside the valid range yields 400 Bad Request."""
    repo = InMemoryBooks()
    asyncio.run(seed(repo))
    client = make_client(repo)

    for params in (
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": -3},
        {"page_size": 101},
    ):
        assert client.get("/books/search", params=params).status_code == 400, params
