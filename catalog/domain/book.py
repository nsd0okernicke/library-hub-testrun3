"""Book entity for the catalog service."""

from __future__ import annotations

from dataclasses import dataclass

from catalog.domain.isbn import Isbn


class InvalidBookDataError(ValueError):
    """Raised when book metadata violates catalog rules."""


@dataclass(slots=True)
class Book:
    """A catalog book: metadata plus the current available stock."""

    isbn: Isbn
    title: str
    author: str
    genre: str
    available_stock: int
    description: str = ""

    def __post_init__(self) -> None:
        for field_name in ("title", "author", "genre"):
            if not getattr(self, field_name):
                raise InvalidBookDataError(f"book {field_name} must not be empty")
        if self.available_stock < 0:
            raise InvalidBookDataError("available_stock must be >= 0")
        if self.description is None:
            self.description = ""
