"""Property-based tests for the SearchBooks use case."""

from __future__ import annotations

import asyncio
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from catalog.application.search_books import SearchBooks
from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.search import SearchQuery, SearchResult
from tests.unit.catalog.fakes import InMemoryBooks

WORDS = st.sampled_from(["alpha", "beta", "Alpha", "GAMMA", "gamma", "delta", "delta2"])


def book_strategy() -> st.SearchStrategy[Book]:
    """Generate books with colliding titles/ISBNs to stress the sort order."""
    return st.builds(
        Book,
        isbn=st.integers(0, 10**8 - 1).map(lambda n: Isbn(f"978-0-1{str(n).zfill(8)}")),
        title=WORDS,
        author=WORDS,
        genre=WORDS,
        available_stock=st.integers(0, 10),
    )


def query_strategy() -> st.SearchStrategy[dict[str, Any]]:
    """Generate valid search queries with optional filters and pagination."""
    return st.fixed_dictionaries(
        {
            "title": st.one_of(st.none(), WORDS),
            "author": st.one_of(st.none(), WORDS),
            "genre": st.one_of(st.none(), WORDS),
            "page": st.integers(1, 10),
            "page_size": st.integers(1, 100),
        }
    )


def search_books(books: list[Book], **kwargs: Any) -> SearchResult:
    """Store the books in a fake repository and run the use case."""
    repo = InMemoryBooks()
    for book in books:
        asyncio.run(repo.save(book))
    return asyncio.run(SearchBooks(repo).execute(SearchQuery(**kwargs)))


def stored_books(books: list[Book]) -> list[Book]:
    """The catalog the repository would hold: duplicates by ISBN removed."""
    unique: dict[str, Book] = {}
    for book in books:
        unique[book.isbn.digits] = book
    return list(unique.values())


def matches_all_filters(book: Book, query: dict[str, Any]) -> bool:
    """Reference filter: every specified filter is a case-insensitive substring."""
    return all(
        (text := query[field]) is None or text.lower() in getattr(book, field).lower()
        for field in ("title", "author", "genre")
    )


@given(books=st.lists(book_strategy(), max_size=25), query=query_strategy())
@settings(max_examples=50)
def test_total_counts_every_match_independently(books: list[Book], query: dict[str, Any]) -> None:
    """The total equals a reference filter applied to the stored catalog."""
    result = search_books(books, **query)
    stored = stored_books(books)
    assert result.total == sum(1 for book in stored if matches_all_filters(book, query))


@given(books=st.lists(book_strategy(), max_size=25), query=query_strategy())
@settings(max_examples=50)
def test_every_returned_book_matches_every_filter(books: list[Book], query: dict[str, Any]) -> None:
    """No returned book violates a specified filter."""
    result = search_books(books, **query)

    for book in result.items:
        for field in ("title", "author", "genre"):
            if (text := query[field]) is not None:
                assert text.lower() in getattr(book, field).lower(), (book, field, text)


@given(books=st.lists(book_strategy(), max_size=25), query=query_strategy())
@settings(max_examples=50)
def test_items_are_sorted_by_title_then_isbn(books: list[Book], query: dict[str, Any]) -> None:
    """The page is always in (title, isbn-digits) ascending order."""
    result = search_books(books, **query)
    keys = [(book.title, book.isbn.digits) for book in result.items]
    assert keys == sorted(keys)


@given(books=st.lists(book_strategy(), max_size=25), query=query_strategy())
@settings(max_examples=50)
def test_page_never_exceeds_page_size_and_slices_the_full_result(
    books: list[Book], query: dict[str, Any]
) -> None:
    """The page is the sorted match list sliced at the requested offset."""
    result = search_books(books, **query)

    expected = sorted(
        (book for book in stored_books(books) if matches_all_filters(book, query)),
        key=lambda book: (book.title, book.isbn.digits),
    )
    start = (query["page"] - 1) * query["page_size"]
    assert [book.isbn.digits for book in result.items] == [
        book.isbn.digits for book in expected[start : start + query["page_size"]]
    ]


@given(books=st.lists(book_strategy(), max_size=25), query=query_strategy())
@settings(max_examples=25)
def test_search_is_idempotent(books: list[Book], query: dict[str, Any]) -> None:
    """The same query on the same catalog yields the same result twice."""
    first = search_books(books, **query)
    second = search_books(books, **query)

    assert [b.isbn.digits for b in first.items] == [b.isbn.digits for b in second.items]
    assert first.total == second.total
    assert first.page == second.page
    assert first.page_size == second.page_size
