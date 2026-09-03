"""Retrieve-book use case for the catalog service."""

from __future__ import annotations

from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository


class RetrieveBook:
    """Returns the stored book for an ISBN.

    Raises ``IsbnValidationError`` for an invalid ISBN format and
    ``BookNotFoundError`` when the ISBN is not in the catalog.
    """

    def __init__(self, books: BookRepository) -> None:
        """Bind the use case to a BookRepository port."""
        self._books = books

    async def execute(self, isbn: str) -> Book:
        """Fetch and return the book stored for the given ISBN."""
        parsed = Isbn(isbn)
        book = await self._books.get_by_isbn(parsed)
        if book is None:
            raise BookNotFoundError(parsed.digits)
        return book
