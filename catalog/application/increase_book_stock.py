"""Manual stock-increase use case for the catalog service."""

from __future__ import annotations

from dataclasses import dataclass

from catalog.domain.book import Book
from catalog.domain.exceptions import BookNotFoundError, InvalidCopiesError
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository


@dataclass(frozen=True)
class IncreaseBookStockCommand:
    """Input for the manual stock-increase use case."""

    isbn: str
    copies: int


class IncreaseBookStock:
    """Adds a manually requested number of copies to a book's available stock.

    A stock increase is a manual operator action: it needs no loan record and
    no BookReturned event. Raises ``IsbnValidationError`` for an invalid ISBN
    format, ``InvalidCopiesError`` for a non-positive copy count, and
    ``BookNotFoundError`` when the ISBN does not exist in the catalog.
    """

    def __init__(self, books: BookRepository) -> None:
        """Bind the use case to a BookRepository port."""
        self._books = books

    async def execute(self, command: IncreaseBookStockCommand) -> Book:
        """Increase the stock of the named book by the requested copies."""
        isbn = Isbn(command.isbn)
        if command.copies <= 0:
            raise InvalidCopiesError(f"copies must be a positive integer, got {command.copies}")
        book = await self._books.get_by_isbn(isbn)
        if book is None:
            raise BookNotFoundError(isbn.digits)
        book.available_stock += command.copies
        await self._books.update(book)
        return book
