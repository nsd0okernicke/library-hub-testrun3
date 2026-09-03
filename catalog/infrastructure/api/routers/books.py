"""HTTP routes for books in the catalog service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from catalog.application.create_book import CreateBook, CreateBookCommand
from catalog.infrastructure.api.schemas import BookCreateRequest

router = APIRouter()


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
    return {
        "isbn": book.isbn.value,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "description": book.description,
        "available_stock": book.available_stock,
    }
