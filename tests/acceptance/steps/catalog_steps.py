"""pytest-bdd step definitions that execute features/cat-3-create-book.feature."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import cfparse
from starlette.testclient import TestClient

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository

_FEATURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "cat-3-create-book.feature"
    )
)

scenarios(_FEATURE_PATH)


def _post_book(context: Any, payload: dict[str, object]) -> None:
    """Record the pre-request catalog size and send POST /books."""
    context.requested_isbn = payload["isbn"]
    repository: BookRepository = context.catalog.repository
    context.catalog_count_before = asyncio.run(repository.count())
    client: TestClient = context.catalog.client
    context.response = client.post("/books", json=payload)


def _requested_book(context: Any) -> Book:
    """Fetch the book created by the last request, failing loudly if absent."""
    assert context.requested_isbn is not None
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(context.requested_isbn)))
    assert book is not None, f"book {context.requested_isbn} not found"
    return book


@given("the catalog service is running")
def catalog_service_running(context: Any, catalog: Any) -> None:
    """Wire the scenario context to the running catalog app."""
    context.catalog = catalog


@given(cfparse('a book with isbn "{isbn}" already exists in the catalog'))
def book_already_exists(context: Any, catalog: Any, isbn: str) -> None:
    """Pre-seed the catalog with a book carrying this ISBN."""
    book = Book(
        isbn=Isbn(isbn),
        title="Pre-seeded Book",
        author="Pre-seeded Author",
        genre="Fiction",
        available_stock=2,
    )
    asyncio.run(catalog.repository.save(book))


@when(
    cfparse(
        'a book is requested with isbn "{isbn}", title "{title}", author "{author}", '
        'genre "{genre}" and initial stock {initial_stock:d}'
    )
)
def book_requested(
    context: Any, isbn: str, title: str, author: str, genre: str, initial_stock: int
) -> None:
    """Send a create-book request with the given metadata and stock."""
    _post_book(
        context,
        {
            "isbn": isbn,
            "title": title,
            "author": author,
            "genre": genre,
            "initial_stock": initial_stock,
        },
    )


@when(
    cfparse(
        'a book is requested with isbn "{isbn}", title "{title}", author "{author}", '
        'genre "{genre}", initial stock {initial_stock:d} and description "{description}"'
    )
)
def book_requested_with_description(
    context: Any,
    isbn: str,
    title: str,
    author: str,
    genre: str,
    initial_stock: int,
    description: str,
) -> None:
    """Send a create-book request that also carries a description."""
    _post_book(
        context,
        {
            "isbn": isbn,
            "title": title,
            "author": author,
            "genre": genre,
            "initial_stock": initial_stock,
            "description": description,
        },
    )


@when(cfparse('a book is requested with isbn "{isbn}"'))
def book_requested_by_isbn_only(context: Any, isbn: str) -> None:
    """Send a create-book request for the ISBN with fixed valid metadata."""
    _post_book(
        context,
        {
            "isbn": isbn,
            "title": "Duplicate Check",
            "author": "Test Author",
            "genre": "Fiction",
            "initial_stock": 1,
        },
    )


@when(cfparse("a book is requested where {problem}"))
def book_requested_with_problem(context: Any, problem: str) -> None:
    """Send a create-book request that violates exactly the named rule."""
    payload: dict[str, object] = {
        "isbn": "978-0-99-123456-0",
        "title": "Problem Book",
        "author": "Test Author",
        "genre": "Fiction",
        "initial_stock": 1,
    }
    if problem == "the title is missing":
        payload.pop("title")
    elif problem == "the author is missing":
        payload.pop("author")
    elif problem == "the genre is missing":
        payload.pop("genre")
    elif problem == "the initial stock is negative (-1)":
        payload["initial_stock"] = -1
    else:
        raise AssertionError(f"unknown problem: {problem!r}")
    _post_book(context, payload)


@then("the request succeeds with a 201 Created")
def request_succeeded(context: Any) -> None:
    """Assert the create-book request returned 201 Created."""
    assert context.response.status_code == 201, context.response.text


@then(cfparse('a book with isbn "{isbn}" exists in the catalog'))
def book_exists(context: Any, isbn: str) -> None:
    """Assert the catalog now holds a book with this ISBN."""
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    assert book is not None


@then(cfparse('its title is "{title}" and its author is "{author}" and its genre is "{genre}"'))
def book_fields_match(context: Any, title: str, author: str, genre: str) -> None:
    """Assert the stored metadata matches the request."""
    book = _requested_book(context)
    assert book.title == title
    assert book.author == author
    assert book.genre == genre


@then(cfparse("its available stock is {initial_stock:d}"))
def book_stock_matches(context: Any, initial_stock: int) -> None:
    """Assert the stored available stock matches the request."""
    assert _requested_book(context).available_stock == initial_stock


@then(cfparse('its description is "{description}"'))
def book_description_matches(context: Any, description: str) -> None:
    """Assert the stored description matches the request."""
    assert _requested_book(context).description == description


@then("the request is rejected with a 409 Conflict")
def request_conflict(context: Any) -> None:
    """Assert the create-book request returned 409 Conflict."""
    assert context.response.status_code == 409, context.response.text


@then(cfparse('the catalog contains exactly one book with isbn "{isbn}"'))
def exactly_one_book_with_isbn(context: Any, isbn: str) -> None:
    """Assert the pre-existing book survived and no second one was added.

    Book identity is the 13-digit ISBN (primary key), so at most one book can
    carry it; finding one confirms the duplicate was rejected.
    """
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    assert book is not None


@then("the request is rejected with a 400 Bad Request")
def request_bad_request(context: Any) -> None:
    """Assert the create-book request returned 400 Bad Request."""
    assert context.response.status_code == 400, context.response.text


@then("no book was added to the catalog")
def no_book_added(context: Any) -> None:
    """Assert the rejected request left the catalog size unchanged."""
    after = asyncio.run(context.catalog.repository.count())
    assert after == context.catalog_count_before
