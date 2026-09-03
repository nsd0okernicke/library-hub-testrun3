"""Unit tests for the HandleBookReturnedEvent use case."""

from __future__ import annotations

from catalog.application.handle_book_returned import HandleBookReturnedEvent
from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from tests.unit.catalog.fakes import InMemoryBooks

GATSBY = "978-0-14-103614-3"


def _gatsby(stock: int) -> Book:
    """Build a Gatsby book with the given initial stock."""
    return Book(
        isbn=Isbn(GATSBY),
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        genre="Fiction",
        available_stock=stock,
    )


async def _seed(stock: int = 4) -> InMemoryBooks:
    """Return an in-memory catalog seeded with one Gatsby book."""
    books = InMemoryBooks()
    await books.save(_gatsby(stock))
    return books


async def _stored_stock(books: InMemoryBooks) -> int | None:
    """Return the stored stock of the Gatsby book, or None when absent."""
    book = await books.get_by_isbn(Isbn(GATSBY))
    return book.available_stock if book is not None else None


async def test_event_increases_stock_of_existing_book_by_one() -> None:
    books = await _seed(stock=4)
    await HandleBookReturnedEvent(books).handle(GATSBY)
    assert await _stored_stock(books) == 5


async def test_each_event_adds_exactly_one_unit() -> None:
    books = await _seed(stock=2)
    handler = HandleBookReturnedEvent(books)
    for _ in range(3):
        await handler.handle(GATSBY)
    assert await _stored_stock(books) == 5


async def test_event_for_unknown_valid_isbn_is_ignored() -> None:
    books = await _seed(stock=4)
    await HandleBookReturnedEvent(books).handle("978-0-00-000000-1")
    assert await books.get_by_isbn(Isbn("978-0-00-000000-1")) is None
    assert await _stored_stock(books) == 4


async def test_event_with_invalid_isbn_format_is_ignored() -> None:
    books = await _seed(stock=4)
    await HandleBookReturnedEvent(books).handle("978-0-14-103614")  # 12 digits
    assert await books.count() == 1
    assert await _stored_stock(books) == 4


async def test_event_with_empty_isbn_is_ignored_without_error() -> None:
    books = await _seed(stock=1)
    await HandleBookReturnedEvent(books).handle("")
    assert await _stored_stock(books) == 1


async def test_metadata_is_unchanged_after_return() -> None:
    books = await _seed(stock=5)
    await HandleBookReturnedEvent(books).handle(GATSBY)
    book = await books.get_by_isbn(Isbn(GATSBY))
    assert book is not None
    assert book.title == "The Great Gatsby"
    assert book.author == "F. Scott Fitzgerald"
    assert book.genre == "Fiction"
    assert book.available_stock == 6


async def test_events_after_ignored_event_still_apply() -> None:
    books = await _seed(stock=1)
    handler = HandleBookReturnedEvent(books)
    await handler.handle("978-0-00-000000-1")  # unknown: ignored
    await handler.handle(GATSBY)
    assert await _stored_stock(books) == 2
