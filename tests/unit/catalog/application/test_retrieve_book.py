"""Unit tests for the RetrieveBook use case with a fake repository."""

from __future__ import annotations

import pytest

from catalog.application.retrieve_book import RetrieveBook
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError
from catalog.domain.isbn import Isbn, IsbnValidationError
from tests.unit.catalog.fakes import InMemoryBooks


def _gatsby() -> Book:
    """A fully described book for the first scenario."""
    return Book(
        isbn=Isbn("978-0-14-103614-3"),
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        genre="Fiction",
        available_stock=5,
        description="A jazz-age novel about money",
    )


async def _seed() -> InMemoryBooks:
    """Return a repository containing one book with and without description."""
    repo = InMemoryBooks()
    await repo.save(_gatsby())
    await repo.save(
        Book(
            isbn=Isbn("978-0-553-21316-7"),
            title="Brave New World",
            author="Aldous Huxley",
            genre="Dystopian",
            available_stock=2,
        )
    )
    return repo


async def test_retrieve_returns_stored_metadata_unchanged() -> None:
    """An existing book is returned with its full metadata and stock."""
    book = await RetrieveBook(await _seed()).execute("978-0-14-103614-3")

    assert book == _gatsby()
    assert book.description == "A jazz-age novel about money"
    assert book.available_stock == 5


async def test_retrieve_without_description_returns_empty_string() -> None:
    """A book created without a description has an empty description."""
    book = await RetrieveBook(await _seed()).execute("978-0-553-21316-7")

    assert book.title == "Brave New World"
    assert book.available_stock == 2
    assert book.description == ""


async def test_retrieve_missing_book_raises_not_found() -> None:
    """A book that is not in the catalog raises BookNotFoundError."""
    with pytest.raises(BookNotFoundError):
        await RetrieveBook(await _seed()).execute("978-0-20-163361-0")


async def test_retrieve_invalid_isbn_raises_validation_error() -> None:
    """An ISBN with a different digit count raises IsbnValidationError."""
    use_case = RetrieveBook(await _seed())

    for invalid in ("978-0-14-103614", "978-0-14-103614-34", "978-0-14-103614-X", "0-14-103614-3"):
        with pytest.raises(IsbnValidationError):
            await use_case.execute(invalid)


async def test_retrieve_is_hyphenation_insensitive() -> None:
    """ISBNs that differ only in hyphenation refer to the same book."""
    book = await RetrieveBook(await _seed()).execute("9780141036143")

    assert book.title == "The Great Gatsby"
