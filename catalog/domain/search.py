"""Search query and result value objects for the catalog service."""

from __future__ import annotations

from dataclasses import dataclass, field

from catalog.domain.book import Book
from catalog.domain.exceptions import InvalidSearchParametersError

#: First page of a paginated search result.
DEFAULT_PAGE = 1
#: Page size applied when the caller does not name one.
DEFAULT_PAGE_SIZE = 20
#: Largest page size the search accepts.
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Immutable search criteria for the catalog.

    A filter that is ``None`` is ignored; a specified filter matches when
    the book's field contains the filter text as a case-insensitive
    substring. ``page`` is 1-indexed and ``page_size`` may not exceed
    ``MAX_PAGE_SIZE``.
    """

    title: str | None = None
    author: str | None = None
    genre: str | None = None
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        """Reject pagination values outside the valid range."""
        if self.page < DEFAULT_PAGE:
            raise InvalidSearchParametersError("page must be >= 1")
        if self.page_size < DEFAULT_PAGE:
            raise InvalidSearchParametersError("page size must be >= 1")
        if self.page_size > MAX_PAGE_SIZE:
            raise InvalidSearchParametersError(f"page size must be <= {MAX_PAGE_SIZE}")


@dataclass(slots=True)
class SearchResult:
    """One page of a catalog search.

    ``items`` holds the books on this page only, in result order;
    ``total`` counts every match, not only this page.
    """

    items: list[Book] = field(default_factory=list)
    total: int = 0
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE
