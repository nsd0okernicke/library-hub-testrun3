"""Port interfaces for the catalog service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn


class BookRepository(ABC):
    """Persistence port for catalog books.

    Identity is the ISBN as a 13-digit string, so ISBNs that differ only in
    hyphenation refer to the same book.
    """

    @abstractmethod
    async def get_by_isbn(self, isbn: Isbn) -> Book | None:
        """Return the book for the ISBN, or None when not present."""

    @abstractmethod
    async def save(self, book: Book) -> None:
        """Insert a new book into the catalog."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of books in the catalog."""
