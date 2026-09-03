"""Pydantic DTOs for the catalog HTTP API."""

from __future__ import annotations

from pydantic import BaseModel


class BookCreateRequest(BaseModel):
    """Payload for POST /books.

    Metadata fields default to empty so that missing data surfaces as a
    400 from the domain layer rather than a 422 from the HTTP layer.
    """

    isbn: str
    title: str = ""
    author: str = ""
    genre: str = ""
    initial_stock: int = 0
    description: str | None = None


class StockIncreaseRequest(BaseModel):
    """Payload for POST /books/{isbn}/stock.

    ``copies`` defaults to zero so that a missing count surfaces as a 400
    from the domain layer rather than a 422 from the HTTP layer.
    """

    copies: int = 0
