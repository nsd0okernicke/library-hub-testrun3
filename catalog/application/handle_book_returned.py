"""Book-returned use case for the catalog service."""

from __future__ import annotations

from catalog.domain.isbn import Isbn, IsbnValidationError
from catalog.domain.ports import BookRepository


class HandleBookReturnedEvent:
    """Applies one consumed BookReturned event to the catalog.

    Increases the available stock of the book with the event's ISBN by
    exactly one. Events whose ISBN does not exist in the catalog — including
    ISBNs that are not in valid 13-digit format — are ignored silently so
    that later events keep being processed.
    """

    def __init__(self, books: BookRepository) -> None:
        """Bind the use case to a BookRepository port."""
        self._books = books

    async def handle(self, isbn: str) -> None:
        """Increase the stock of the named book by one, ignoring unknown ISBNs."""
        try:
            isbn_value = Isbn(isbn)
        except IsbnValidationError:
            return
        book = await self._books.get_by_isbn(isbn_value)
        if book is None:
            return
        book.available_stock += 1
        await self._books.update(book)
