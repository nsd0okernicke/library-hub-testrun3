"""Contract tests for the catalog port interfaces."""

import pytest

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository


def test_book_repository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BookRepository()  # type: ignore[abstract]


class _PartialBookRepository(BookRepository):
    """Concrete class that implements only two of the five port methods."""

    async def get_by_isbn(self, isbn: Isbn) -> Book | None:
        return None

    async def count(self) -> int:
        return 0


def test_partial_implementation_stays_abstract() -> None:
    """A port implementation missing a method must not be instantiable."""
    with pytest.raises(TypeError):
        _PartialBookRepository()  # type: ignore[abstract]
