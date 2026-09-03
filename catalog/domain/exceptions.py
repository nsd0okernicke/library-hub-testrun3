"""Domain exceptions for the catalog service."""

from __future__ import annotations


class BookAlreadyExistsError(Exception):
    """Raised when creating a book whose ISBN already exists in the catalog."""

    def __init__(self, isbn: str) -> None:
        """Create the error, remembering the offending ISBN."""
        super().__init__(f"book with ISBN {isbn} already exists")
        self.isbn = isbn
