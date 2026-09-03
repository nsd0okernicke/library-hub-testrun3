"""Property-based tests for the HandleBookReturnedEvent use case."""

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from catalog.application.handle_book_returned import HandleBookReturnedEvent
from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from tests.unit.catalog.fakes import InMemoryBooks

GATSBY = "978-0-14-103614-3"
_GATSBY_DIGITS = "9780141036143"


def _seeded_catalog(initial_stock: int) -> InMemoryBooks:
    """Return an in-memory catalog holding one Gatsby book."""
    books = InMemoryBooks()
    asyncio.run(
        books.save(
            Book(
                isbn=Isbn(GATSBY),
                title="The Great Gatsby",
                author="F. Scott Fitzgerald",
                genre="Fiction",
                available_stock=initial_stock,
            )
        )
    )
    return books


@settings(max_examples=50)
@given(initial=st.integers(0, 1000), returns=st.integers(0, 100))
def test_stock_after_returns_is_initial_plus_n(initial: int, returns: int) -> None:
    """After n return events the stock is exactly the initial stock plus n."""
    books = _seeded_catalog(initial)

    async def drive() -> Book:
        """Apply n return events and return the stored book."""
        handler = HandleBookReturnedEvent(books)
        for _ in range(returns):
            await handler.handle(GATSBY)
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored

    stored = asyncio.run(drive())
    assert stored.available_stock == initial + returns


@settings(max_examples=50)
@given(raw_isbn=st.text())
def test_arbitrary_isbn_strings_are_consumed_safely(raw_isbn: str) -> None:
    """Any string is a safe event payload: no error, catalog left consistent."""
    books = _seeded_catalog(7)
    asyncio.run(HandleBookReturnedEvent(books).handle(raw_isbn))
    assert asyncio.run(books.count()) == 1
    stored = asyncio.run(books.get_by_isbn(Isbn(GATSBY)))
    assert stored is not None
    if raw_isbn.replace("-", "") == _GATSBY_DIGITS:
        assert stored.available_stock == 8
    else:
        assert stored.available_stock == 7
