"""Domain exceptions for the catalog service."""

from __future__ import annotations


class BookAlreadyExistsError(Exception):
    """Raised when creating a book whose ISBN already exists in the catalog."""

    def __init__(self, isbn: str) -> None:
        """Create the error, remembering the offending ISBN."""
        super().__init__(f"book with ISBN {isbn} already exists")
        self.isbn = isbn


class BookNotFoundError(Exception):
    """Raised when retrieving a book whose ISBN is not in the catalog."""

    def __init__(self, isbn: str) -> None:
        """Create the error, remembering the missing ISBN."""
        super().__init__(f"book with ISBN {isbn} not found")
        self.isbn = isbn


class InvalidSearchParametersError(ValueError):
    """Raised when a catalog search names an invalid page or page size."""
