"""Property tests for the RetrieveBook use case."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from catalog.application.retrieve_book import RetrieveBook
from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError
from catalog.domain.isbn import Isbn, IsbnValidationError
from tests.unit.catalog.fakes import InMemoryBooks

_STORED_DIGITS = "9780141036143"


def _hyphenations() -> st.SearchStrategy[str]:
    """Every way of inserting hyphens between the stored 13 digits."""

    @st.composite
    def hyphenation(draw: st.DrawFn) -> str:
        mask = draw(st.integers(min_value=0, max_value=(1 << 12) - 1))
        parts = [_STORED_DIGITS[0]]
        for i, digit in enumerate(_STORED_DIGITS[1:]):
            parts.append("-" if mask & (1 << i) else "")
            parts.append(digit)
        return "".join(parts)

    return hyphenation()


async def _seeded_repo() -> InMemoryBooks:
    """Return a repository containing one book under a fixed ISBN."""
    repo = InMemoryBooks()
    await repo.save(
        Book(
            isbn=Isbn(_STORED_DIGITS),
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            genre="Fiction",
            available_stock=5,
            description="A jazz-age novel about money",
        )
    )
    return repo


@given(_hyphenations())
@settings(max_examples=100)
def test_retrieval_is_hyphenation_invariant(requested: str) -> None:
    """Any hyphenation of the stored 13 digits retrieves the same book."""
    use_case = RetrieveBook(asyncio.run(_seeded_repo()))

    book = asyncio.run(use_case.execute(requested))

    assert book.title == "The Great Gatsby"
    assert book.isbn.digits == _STORED_DIGITS


def test_repeated_retrieval_returns_the_same_book() -> None:
    """Reading a book twice in different formats returns equal metadata."""
    use_case = RetrieveBook(asyncio.run(_seeded_repo()))
    first = asyncio.run(use_case.execute("978-0-14-103614-3"))
    second = asyncio.run(use_case.execute("9780141036143"))

    assert first == second


def test_retrieving_an_absent_isbn_raises() -> None:
    """An ISBN not in the catalog is rejected, whatever its format."""
    use_case = RetrieveBook(asyncio.run(_seeded_repo()))

    with pytest.raises(BookNotFoundError):
        asyncio.run(use_case.execute("978-0-20-163361-0"))


def test_retrieving_an_invalid_isbn_raises() -> None:
    """A malformed ISBN never reaches the repository."""
    use_case = RetrieveBook(asyncio.run(_seeded_repo()))

    with pytest.raises(IsbnValidationError):
        asyncio.run(use_case.execute("not an isbn"))
