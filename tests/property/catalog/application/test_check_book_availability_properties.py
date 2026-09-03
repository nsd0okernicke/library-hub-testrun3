"""Property tests for the CheckBookAvailability use case and value object."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from catalog.application.check_book_availability import CheckBookAvailability
from catalog.domain.availability import AvailabilityStatus, InvalidAvailabilityError
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError
from catalog.domain.isbn import Isbn, IsbnValidationError
from tests.property.catalog.application.test_retrieve_book_properties import (
    _STORED_DIGITS,
    _hyphenations,
)
from tests.unit.catalog.fakes import InMemoryBooks


async def _seeded_repo(stock: int) -> InMemoryBooks:
    """Return a repository containing one book with the given stock."""
    repo = InMemoryBooks()
    await repo.save(
        Book(
            isbn=Isbn(_STORED_DIGITS),
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            genre="Fiction",
            available_stock=stock,
        )
    )
    return repo


@given(_hyphenations(), st.integers(min_value=0, max_value=1000))
@settings(max_examples=100)
def test_availability_is_hyphenation_invariant(requested: str, stock: int) -> None:
    """Any hyphenation of the stored 13 digits reports the same availability."""
    use_case = CheckBookAvailability(asyncio.run(_seeded_repo(stock)))

    status = asyncio.run(use_case.execute(requested))

    assert status.available_count == stock
    assert status.isbn == requested


def test_repeated_check_reports_the_same_availability() -> None:
    """Checking twice in different formats yields equal availability counts."""
    use_case = CheckBookAvailability(asyncio.run(_seeded_repo(7)))
    first = asyncio.run(use_case.execute("978-0-14-103614-3"))
    second = asyncio.run(use_case.execute("9780141036143"))

    assert first.available_count == second.available_count


@given(st.integers(min_value=0, max_value=10_000))
@settings(max_examples=50)
def test_availability_status_accepts_any_non_negative_count(count: int) -> None:
    """Every non-negative count is a valid availability state."""
    status = AvailabilityStatus(isbn=_STORED_DIGITS, available_count=count)

    assert status.available_count == count


def test_availability_status_rejects_negative_counts() -> None:
    """Any negative count violates the availability invariant."""
    with pytest.raises(InvalidAvailabilityError):
        AvailabilityStatus(isbn=_STORED_DIGITS, available_count=-1)


def test_checking_an_absent_isbn_raises() -> None:
    """An ISBN not in the catalog is rejected, whatever its format."""
    use_case = CheckBookAvailability(asyncio.run(_seeded_repo(5)))

    with pytest.raises(BookNotFoundError):
        asyncio.run(use_case.execute("978-0-20-163361-0"))


def test_checking_an_invalid_isbn_raises() -> None:
    """A malformed ISBN never reaches the repository."""
    use_case = CheckBookAvailability(asyncio.run(_seeded_repo(5)))

    with pytest.raises(IsbnValidationError):
        asyncio.run(use_case.execute("not an isbn"))
