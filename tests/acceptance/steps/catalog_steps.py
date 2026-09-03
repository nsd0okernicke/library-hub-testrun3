"""pytest-bdd step definitions that execute features/cat-3-create-book.feature."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from pytest_bdd import given, scenarios, then, when
from pytest_bdd.parsers import cfparse
from pytest_bdd.parsers import re as re_parser
from starlette.testclient import TestClient

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository

_FEATURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "cat-3-create-book.feature"
    )
)

_FEATURE_RETRIEVE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "features",
        "cat-5-retrieve-book-by-isbn.feature",
    )
)

_FEATURE_SEARCH_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "features", "cat-1-search-books.feature"
    )
)

_FEATURE_AVAILABILITY_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "features",
        "cat-2-check-book-availability.feature",
    )
)

scenarios(_FEATURE_PATH)
scenarios(_FEATURE_RETRIEVE_PATH)
scenarios(_FEATURE_SEARCH_PATH)
scenarios(_FEATURE_AVAILABILITY_PATH)


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
    """Assert the available stock matches the request.

    When the last request was a successful retrieval (200), the stock is
    asserted from the response body; for create-book requests (201) it is
    asserted against the stored book.
    """
    response = getattr(context, "response", None)
    if response is not None and response.status_code == 200:
        assert response.json()["available_stock"] == initial_stock, response.text
        return
    assert _requested_book(context).available_stock == initial_stock


@then(cfparse('its description is "{description}"'))
def book_description_matches(context: Any, description: str) -> None:
    """Assert the stored description matches the request."""
    assert _requested_book(context).description == description


@then(cfparse('the catalog contains exactly one book with isbn "{isbn}"'))
def exactly_one_book_with_isbn(context: Any, isbn: str) -> None:
    """Assert the pre-existing book survived and no second one was added.

    Book identity is the 13-digit ISBN (primary key), so at most one book can
    carry it; finding one confirms the duplicate was rejected.
    """
    book = asyncio.run(context.catalog.repository.get_by_isbn(Isbn(isbn)))
    assert book is not None


@given(
    cfparse(
        'a book with isbn "{isbn}", title "{title}", author "{author}", genre "'
        '{genre}", description "{description}" and initial stock {stock:d}'
    )
)
def book_with_description_seeded(
    context: Any, isbn: str, title: str, author: str, genre: str, description: str, stock: int
) -> None:
    """Seed the catalog with a fully described book ready to be retrieved."""
    asyncio.run(
        context.catalog.repository.save(
            Book(
                isbn=Isbn(isbn),
                title=title,
                author=author,
                genre=genre,
                available_stock=stock,
                description=description,
            )
        )
    )


@given(
    cfparse(
        'a book with isbn "{isbn}", title "{title}", author "{author}", genre "'
        '{genre}" and initial stock {stock:d}'
    )
)
def book_without_description_seeded(
    context: Any, isbn: str, title: str, author: str, genre: str, stock: int
) -> None:
    """Seed the catalog with a book created without a description."""
    asyncio.run(
        context.catalog.repository.save(
            Book(
                isbn=Isbn(isbn),
                title=title,
                author=author,
                genre=genre,
                available_stock=stock,
            )
        )
    )


@when(cfparse('the book with isbn "{isbn}" is requested'))
def retrieve_book_requested(context: Any, isbn: str) -> None:
    """Send a GET /books/{isbn} request for the given ISBN."""
    client: TestClient = context.catalog.client
    context.response = client.get(f"/books/{isbn}")


@then("the request succeeds with a 200 OK")
def retrieve_succeeded(context: Any) -> None:
    """Assert the retrieve request returned 200 OK."""
    assert context.response.status_code == 200, context.response.text


@then(
    cfparse(
        'the response contains isbn "{isbn}", title "{title}", author "'
        '{author}", genre "{genre}" and description "{description}"'
    )
)
def retrieve_response_contains_full_metadata(
    context: Any, isbn: str, title: str, author: str, genre: str, description: str
) -> None:
    """Assert the response carries the stored metadata unchanged."""
    body = context.response.json()
    assert body["isbn"] == isbn
    assert body["title"] == title
    assert body["author"] == author
    assert body["genre"] == genre
    assert body["description"] == description


@then(cfparse('the response contains title "{title}", author "{author}" and genre "{genre}"'))
def retrieve_response_contains_metadata(context: Any, title: str, author: str, genre: str) -> None:
    """Assert the response carries the stored title, author and genre."""
    body = context.response.json()
    assert body["title"] == title
    assert body["author"] == author
    assert body["genre"] == genre


@then("its description is empty")
def retrieve_response_description_empty(context: Any) -> None:
    """Assert the response description of a description-less book is empty."""
    assert context.response.json()["description"] == ""


@then("the request is rejected with a 404 Not Found")
def retrieve_rejected_not_found(context: Any) -> None:
    """Assert the retrieve request for a missing book returned 404."""
    assert context.response.status_code == 404, context.response.text


# ---------------------------------------------------------------------------
# cat-2-check-book-availability.feature: availability by ISBN
# ---------------------------------------------------------------------------


@when(cfparse('the availability of the book with isbn "{isbn}" is requested'))
def availability_requested(context: Any, isbn: str) -> None:
    """Send a GET /books/{isbn}/availability request for the given ISBN."""
    client: TestClient = context.catalog.client
    context.response = client.get(f"/books/{isbn}/availability")


@then(cfparse('the response contains only isbn "{isbn}" and available stock {stock:d}'))
def availability_response_contains_isbn_and_stock(context: Any, isbn: str, stock: int) -> None:
    """Assert the response carries the ISBN and the current available stock."""
    body = context.response.json()
    assert body["isbn"] == isbn, context.response.text
    assert body["available_count"] == stock, context.response.text


@then("the response contains no title, author, genre or description")
def availability_response_has_no_metadata(context: Any) -> None:
    """Assert the availability response exposes no other book metadata."""
    assert set(context.response.json()) == {"isbn", "available_count"}, context.response.text


@then("no book was added to the catalog")
def no_book_added(context: Any) -> None:
    """Assert the rejected request left the catalog size unchanged."""
    after = asyncio.run(context.catalog.repository.count())
    assert after == context.catalog_count_before


# ---------------------------------------------------------------------------
# cat-1-search-books.feature: search by title/author/genre with pagination
# ---------------------------------------------------------------------------


def _search(context: Any, **params: object) -> None:
    """Send GET /books/search with the given query parameters."""
    client: TestClient = context.catalog.client
    context.response = client.get("/books/search", params=params)


def _result_titles(context: Any) -> list[str]:
    """Extract the result titles from the last search response, in order."""
    return [item["title"] for item in context.response.json()["items"]]


def _expected_titles(raw: str) -> list[str]:
    """Parse a Gherkin titles list like '"Dune", "Refactoring" and "The Hobbit"'."""
    return re.findall(r'"([^"]*)"', raw)


def _assert_titles_exact(context: Any, titles: str) -> None:
    """Assert the result list contains exactly the named titles, in order."""
    expected = _expected_titles(titles)
    assert _result_titles(context) == expected, context.response.text


@given("the catalog is pre-seeded with:", target_fixture="seeded_books")
def catalog_pre_seeded(context: Any, catalog: Any, datatable: Any) -> None:
    """Pre-seed the catalog with the books from the step's table."""
    rows: list[list[str]] = []
    for row in list(datatable)[1:]:  # first row is the table header
        isbn, title, author, genre = (str(cell) for cell in row)
        book = Book(isbn=Isbn(isbn), title=title, author=author, genre=genre, available_stock=1)
        asyncio.run(catalog.repository.save(book))
        rows.append([isbn, title, author, genre])
    return rows


@when("the catalog is searched")
def search_without_filters(context: Any) -> None:
    """Send an unfiltered search request."""
    _search(context)


@when(cfparse('the catalog is searched with title "{title}" and author "{author}"'))
def search_with_title_and_author(context: Any, title: str, author: str) -> None:
    """Send a search combining a title and an author filter."""
    _search(context, title=title, author=author)


@when(re_parser(r'the catalog is searched with (?P<field>\w+) "(?P<text>[^"]+)"'))
def search_with_single_filter(context: Any, field: str, text: str) -> None:
    """Send a search filtered on exactly the named field."""
    assert field in ("title", "author", "genre"), field
    _search(context, **{field: text})


@when(cfparse("the catalog is searched with page {page:d} and page size {page_size:d}"))
def search_with_pagination(context: Any, page: int, page_size: int) -> None:
    """Send a search for the named page and page size."""
    _search(context, page=page, page_size=page_size)


@when(re_parser(r"the catalog is searched where the (?P<which>page(?: size)?) is (?P<value>-?\d+)"))
def search_with_invalid_pagination(context: Any, which: str, value: str) -> None:
    """Send a search whose named page or page size is out of range."""
    param = "page_size" if which == "page size" else "page"
    _search(context, **{param: int(value)})


@then(re_parser(r"the result list contains exactly (?P<titles>.+) in this order"))
def result_list_exact_in_order(context: Any, titles: str) -> None:
    """Assert the result list contains exactly the named titles, in order."""
    _assert_titles_exact(context, titles)


@then(re_parser(r"the result list contains exactly (?P<titles>.+)"))
def result_list_exact(context: Any, titles: str) -> None:
    """Assert the result list contains exactly the named titles."""
    _assert_titles_exact(context, titles)


@then("the result list is empty")
def result_list_empty(context: Any) -> None:
    """Assert the search returned no books."""
    assert context.response.json()["items"] == [], context.response.text


@then(cfparse("the total count is {total:d}"))
def total_count_is(context: Any, total: int) -> None:
    """Assert the response reports the expected total match count."""
    assert context.response.json()["total"] == total, context.response.text


@then(cfparse("the response reports page {page:d} and page size {page_size:d}"))
def response_reports_pagination(context: Any, page: int, page_size: int) -> None:
    """Assert the response echoes the page and page size applied."""
    body = context.response.json()
    assert body["page"] == page, context.response.text
    assert body["page_size"] == page_size, context.response.text
