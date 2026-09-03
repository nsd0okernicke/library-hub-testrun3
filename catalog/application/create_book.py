"""Create-book use case for the catalog service."""

from __future__ import annotations

from dataclasses import dataclass

from catalog.domain.book import Book
from catalog.domain.exceptions import BookAlreadyExistsError
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository


@dataclass(frozen=True)
class CreateBookCommand:
    """Input for the create-book use case."""

    isbn: str
    title: str
    author: str
    genre: str
    initial_stock: int
    description: str = ""


class CreateBook:
    """Registers a new book with its metadata and initial stock.

    Raises ``IsbnValidationError`` for an invalid ISBN format,
    ``InvalidBookDataError`` for missing required data or a negative stock,
    and ``BookAlreadyExistsError`` when the ISBN is already in the catalog.
    """

    def __init__(self, books: BookRepository) -> None:
        """Bind the use case to a BookRepository port."""
        self._books = books

    async def execute(self, command: CreateBookCommand) -> Book:
        """Create and persist the book described by the command."""
        isbn = Isbn(command.isbn)
        book = Book(
            isbn=isbn,
            title=command.title,
            author=command.author,
            genre=command.genre,
            available_stock=command.initial_stock,
            description=command.description or "",
        )
        if await self._books.get_by_isbn(isbn) is not None:
            raise BookAlreadyExistsError(isbn.digits)
        await self._books.save(book)
        return book
