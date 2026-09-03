"""HTTP routes for books in the catalog service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from catalog.application.create_book import CreateBook, CreateBookCommand
from catalog.application.retrieve_book import RetrieveBook
from catalog.domain.book import Book
from catalog.infrastructure.api.schemas import BookCreateRequest

router = APIRouter()


def _book_payload(book: Book) -> dict[str, object]:
    """Shape a Book into its HTTP response representation."""
    return {
        "isbn": book.isbn.value,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "description": book.description,
        "available_stock": book.available_stock,
    }


@router.post("/books", status_code=201)
async def create_book(payload: BookCreateRequest, request: Request) -> dict[str, object]:
    """Create a new book and return its stored metadata."""
    command = CreateBookCommand(
        isbn=payload.isbn,
        title=payload.title,
        author=payload.author,
        genre=payload.genre,
        initial_stock=payload.initial_stock,
        description=payload.description or "",
    )
    use_case: CreateBook = request.app.state.create_book
    book = await use_case.execute(command)
    return _book_payload(book)


@router.get("/books/{isbn}")
async def retrieve_book(isbn: str, request: Request) -> dict[str, object]:
    """Return the stored metadata and available stock for a single book.

    The ISBN is echoed in the format the client requested; the catalog keys
    books by their 13-digit form, so hyphenation is display-only.
    """
    use_case: RetrieveBook = request.app.state.retrieve_book
    payload = _book_payload(await use_case.execute(isbn))
    payload["isbn"] = isbn
    return payload
