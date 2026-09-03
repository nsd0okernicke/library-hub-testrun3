"""HTTP routes for books in the catalog service."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from catalog.application.check_book_availability import CheckBookAvailability
from catalog.application.create_book import CreateBook, CreateBookCommand
from catalog.application.retrieve_book import RetrieveBook
from catalog.application.search_books import SearchBooks
from catalog.domain.book import Book
from catalog.domain.search import SearchQuery
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


@router.get("/books/search")
async def search_books(
    request: Request,
    title: str | None = Query(default=None),
    author: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=20),
) -> dict[str, object]:
    """Return one page of books matching the optional filters.

    A specified filter matches when the book's field contains the filter
    text as a case-insensitive substring; every specified filter must
    match. ``page`` and ``page_size`` outside their valid range are
    rejected with 400 Bad Request.
    """
    use_case: SearchBooks = request.app.state.search_books
    result = await use_case.execute(
        SearchQuery(title=title, author=author, genre=genre, page=page, page_size=page_size)
    )
    return {
        "items": [_book_payload(book) for book in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


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


@router.get("/books/{isbn}/availability")
async def check_book_availability(isbn: str, request: Request) -> dict[str, object]:
    """Return only the ISBN and available count for a single book.

    The ISBN is echoed in the format the client requested; the catalog keys
    books by their 13-digit form, so hyphenation is display-only.
    """
    use_case: CheckBookAvailability = request.app.state.check_book_availability
    status = await use_case.execute(isbn)
    return {"isbn": status.isbn, "available_count": status.available_count}
