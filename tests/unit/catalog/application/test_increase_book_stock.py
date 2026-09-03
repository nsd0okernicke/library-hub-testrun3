"""Unit tests for the IncreaseBookStock use case."""

from __future__ import annotations

import pytest

from catalog.application.increase_book_stock import (
    IncreaseBookStock,
    IncreaseBookStockCommand,
)
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError, InvalidCopiesError
from catalog.domain.isbn import Isbn, IsbnValidationError
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


def _execute(books: InMemoryBooks, isbn: str, copies: int):
    """Run the use case with the given ISBN and copy count."""
    return IncreaseBookStock(books).execute(IncreaseBookStockCommand(isbn=isbn, copies=copies))


async def test_copies_are_added_to_available_stock() -> None:
    """The stock increases by exactly the requested number of copies."""
    books = await _seed(stock=5)
    await _execute(books, GATSBY, 3)
    book = await books.get_by_isbn(Isbn(GATSBY))
    assert book is not None
    assert book.available_stock == 8


async def test_metadata_is_unchanged_after_stock_increase() -> None:
    """A stock increase preserves the book's title, author and genre."""
    books = await _seed(stock=0)
    book = await _execute(books, GATSBY, 1)
    assert book.title == "The Great Gatsby"
    assert book.author == "F. Scott Fitzgerald"
    assert book.genre == "Fiction"


async def test_stock_increase_persists_the_updated_book() -> None:
    """The increased stock is stored, not just returned."""
    books = await _seed(stock=12)
    await _execute(books, GATSBY, 10)
    stored = await books.get_by_isbn(Isbn(GATSBY))
    assert stored is not None
    assert stored.available_stock == 22


async def test_stock_increase_works_without_any_loan_record() -> None:
    """The use case needs no loan context; an empty catalog with one book suffices."""
    books = await _seed(stock=2)
    book = await _execute(books, GATSBY, 4)
    assert book.available_stock == 6


async def test_unknown_isbn_is_rejected_without_creating_a_book() -> None:
    """A stock increase for a valid but unknown ISBN raises and creates nothing."""
    books = await _seed(stock=4)
    with pytest.raises(BookNotFoundError):
        await _execute(books, "978-0-20-163361-0", 2)
    assert await books.get_by_isbn(Isbn("978-0-20-163361-0")) is None
    gatsby = await books.get_by_isbn(Isbn(GATSBY))
    assert gatsby is not None
    assert gatsby.available_stock == 4


async def test_invalid_isbn_format_is_rejected() -> None:
    """An ISBN outside the 13-digit format is rejected with 400-level errors."""
    books = await _seed(stock=4)
    for isbn in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        with pytest.raises(IsbnValidationError):
            await _execute(books, isbn, 2)
    assert await books.count() == 1


async def test_non_positive_copies_are_rejected() -> None:
    """Zero and negative copy counts are rejected without touching the stock."""
    books = await _seed(stock=4)
    for copies in (0, -3):
        with pytest.raises(InvalidCopiesError):
            await _execute(books, GATSBY, copies)
    book = await books.get_by_isbn(Isbn(GATSBY))
    assert book is not None
    assert book.available_stock == 4
