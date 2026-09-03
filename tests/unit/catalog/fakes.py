"""Shared fakes for catalog unit tests."""

from __future__ import annotations

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository


class InMemoryBooks(BookRepository):
    """In-memory fake of the BookRepository port.

    Books are keyed by their 13-digit ISBN, so ISBNs that differ only in
    hyphenation refer to the same book.
    """

    def __init__(self) -> None:
        """Start with an empty catalog."""
        self.books: dict[str, Book] = {}

    async def get_by_isbn(self, isbn: Isbn) -> Book | None:
        """Return the book for the ISBN, or None when not present."""
        return self.books.get(isbn.digits)

    async def save(self, book: Book) -> None:
        """Insert a book into the in-memory catalog."""
        self.books[book.isbn.digits] = book

    async def count(self) -> int:
        """Return the total number of books in the catalog."""
        return len(self.books)

    async def list_all(self) -> list[Book]:
        """Return every book currently in the catalog."""
        return list(self.books.values())
