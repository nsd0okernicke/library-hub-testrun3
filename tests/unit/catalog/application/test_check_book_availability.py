"""Unit tests for the CheckBookAvailability use case with a fake repository."""

from __future__ import annotations

import pytest

from catalog.application.check_book_availability import CheckBookAvailability
from catalog.domain.availability import AvailabilityStatus
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError
from catalog.domain.isbn import Isbn, IsbnValidationError
from tests.unit.catalog.fakes import InMemoryBooks


async def _seeded_repo() -> InMemoryBooks:
    """Return a repository with one book in stock and one out of stock."""
    repo = InMemoryBooks()
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
    return repo


async def test_availability_of_existing_book_reports_stock() -> None:
    """An existing book is returned with its current available stock."""
    status = await CheckBookAvailability(await _seeded_repo()).execute("978-0-14-103614-3")

    assert status == AvailabilityStatus(isbn="978-0-14-103614-3", available_count=5)


async def test_availability_of_out_of_stock_book_reports_zero() -> None:
    """An out-of-stock book is reported with an available count of zero."""
    status = await CheckBookAvailability(await _seeded_repo()).execute("978-0-06-112008-4")

    assert status == AvailabilityStatus(isbn="978-0-06-112008-4", available_count=0)


async def test_availability_missing_book_raises_not_found() -> None:
    """A book that is not in the catalog raises BookNotFoundError."""
    with pytest.raises(BookNotFoundError):
        await CheckBookAvailability(await _seeded_repo()).execute("978-0-20-163361-0")


async def test_availability_invalid_isbn_raises_validation_error() -> None:
    """An ISBN with a different digit count or a letter raises IsbnValidationError."""
    use_case = CheckBookAvailability(await _seeded_repo())

    for invalid in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        with pytest.raises(IsbnValidationError):
            await use_case.execute(invalid)


async def test_availability_is_hyphenation_insensitive() -> None:
    """ISBNs that differ only in hyphenation refer to the same book."""
    status = await CheckBookAvailability(await _seeded_repo()).execute("9780141036143")

    assert status.available_count == 5
