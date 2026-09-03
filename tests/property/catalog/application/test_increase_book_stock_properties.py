"""Property-based tests for the IncreaseBookStock use case."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from catalog.application.increase_book_stock import (
    IncreaseBookStock,
    IncreaseBookStockCommand,
)
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError, InvalidCopiesError
from catalog.domain.isbn import Isbn, IsbnValidationError
from tests.unit.catalog.fakes import InMemoryBooks

GATSBY = "978-0-14-103614-3"


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
@given(initial=st.integers(0, 10_000), copies=st.integers(1, 10_000))
def test_stock_after_increase_is_initial_plus_copies(initial: int, copies: int) -> None:
    """After one valid increase the stock is exactly the initial stock plus copies."""
    books = _seeded_catalog(initial)

    async def drive() -> Book:
        """Apply the stock increase and return the stored book."""
        await IncreaseBookStock(books).execute(IncreaseBookStockCommand(isbn=GATSBY, copies=copies))
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored

    stored = asyncio.run(drive())
    assert stored.available_stock == initial + copies


@settings(max_examples=50)
@given(copies=st.integers(1, 50))
def test_repeated_increases_are_exactly_additive(copies: int) -> None:
    """Each successive increase adds exactly its copy count."""
    books = _seeded_catalog(0)

    async def drive() -> Book:
        """Apply the same increase several times and return the stored book."""
        use_case = IncreaseBookStock(books)
        for _ in range(4):
            await use_case.execute(IncreaseBookStockCommand(isbn=GATSBY, copies=copies))
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored

    stored = asyncio.run(drive())
    assert stored.available_stock == 4 * copies


@settings(max_examples=50)
@given(copies=st.integers(-1000, 0))
def test_non_positive_copies_are_rejected_without_side_effects(copies: int) -> None:
    """Zero and negative copy counts are rejected and leave the stock untouched."""
    books = _seeded_catalog(9)

    async def drive() -> None:
        """Assert the rejection and that nothing was persisted."""
        with pytest.raises(InvalidCopiesError):
            await IncreaseBookStock(books).execute(
                IncreaseBookStockCommand(isbn=GATSBY, copies=copies)
            )
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        assert stored.available_stock == 9

    asyncio.run(drive())


@settings(max_examples=50)
@given(seed=st.integers(0, 100))
def test_increase_preserves_all_metadata(seed: int) -> None:
    """A stock increase never changes title, author or genre."""
    books = _seeded_catalog(seed)

    async def drive() -> Book:
        """Apply one increase and return the stored book."""
        await IncreaseBookStock(books).execute(IncreaseBookStockCommand(isbn=GATSBY, copies=1))
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored

    stored = asyncio.run(drive())
    assert stored.title == "The Great Gatsby"
    assert stored.author == "F. Scott Fitzgerald"
    assert stored.genre == "Fiction"


@settings(max_examples=50)
@given(copies=st.integers(1, 100))
def test_unknown_isbn_is_rejected_and_creates_nothing(copies: int) -> None:
    """A valid but unknown ISBN is rejected without creating a book or changing stock."""
    books = _seeded_catalog(4)

    async def drive() -> int:
        """Assert the rejection and return the stored Gatsby stock."""
        with pytest.raises(BookNotFoundError):
            await IncreaseBookStock(books).execute(
                IncreaseBookStockCommand(isbn="978-0-99-123456-7", copies=copies)
            )
        assert await books.count() == 1
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored.available_stock

    assert asyncio.run(drive()) == 4


@settings(max_examples=50)
@given(raw_isbn=st.text())
def test_arbitrary_isbn_strings_reject_or_apply_safely(raw_isbn: str) -> None:
    """Any ISBN string either matches the known book exactly or is rejected."""
    books = _seeded_catalog(3)

    async def drive() -> int:
        """Apply the increase with the raw ISBN and return the stored stock."""
        try:
            await IncreaseBookStock(books).execute(
                IncreaseBookStockCommand(isbn=raw_isbn, copies=1)
            )
        except IsbnValidationError:
            pass
        stored = await books.get_by_isbn(Isbn(GATSBY))
        assert stored is not None
        return stored.available_stock

    stock = asyncio.run(drive())
    if raw_isbn.replace("-", "") == "9780141036143":
        assert stock == 4
    else:
        assert stock == 3
