"""Search-books use case for the catalog service."""

from __future__ import annotations

from catalog.domain.book import Book
from catalog.domain.ports import BookRepository
from catalog.domain.search import SearchQuery, SearchResult

_FIELDS = ("title", "author", "genre")


def _matches(book: Book, query: SearchQuery) -> bool:
    """Return True when the book matches every specified filter of the query."""
    return all(
        (text := getattr(query, field)) is None or text.lower() in getattr(book, field).lower()
        for field in _FIELDS
    )


class SearchBooks:
    """Returns one page of books matching the query's optional filters.

    A specified filter matches when the book's field contains the filter
    text as a case-insensitive substring, and a book is returned only when
    it matches every specified filter. Results are sorted by title
    ascending, ties by ISBN ascending, and sliced into the requested page.
    """

    def __init__(self, books: BookRepository) -> None:
        """Bind the use case to a BookRepository port."""
        self._books = books

    async def execute(self, query: SearchQuery) -> SearchResult:
        """Filter, sort and paginate the catalog for the given query."""
        matches = sorted(
            (book for book in await self._books.list_all() if _matches(book, query)),
            key=lambda book: (book.title, book.isbn.digits),
        )
        start = (query.page - 1) * query.page_size
        return SearchResult(
            items=matches[start : start + query.page_size],
            total=len(matches),
            page=query.page,
            page_size=query.page_size,
        )
