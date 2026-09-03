"""SQLAlchemy implementation of the BookRepository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from catalog.domain.book import Book
from catalog.domain.isbn import Isbn
from catalog.domain.ports import BookRepository
from catalog.infrastructure.db.models import BookRow


def _to_domain(row: BookRow) -> Book:
    """Map an ORM row to the Book domain entity."""
    return Book(
        isbn=Isbn(row.isbn),
        title=row.title,
        author=row.author,
        genre=row.genre,
        available_stock=row.available_stock,
        description=row.description,
    )


class SqlAlchemyBookRepository(BookRepository):
    """Persists books in PostgreSQL through SQLAlchemy (asyncpg driver)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind the repository to a session factory."""
        self._sessions = sessions

    async def get_by_isbn(self, isbn: Isbn) -> Book | None:
        """Return the book for the ISBN, or None when not present."""
        async with self._sessions() as session:
            row = await session.get(BookRow, isbn.digits)
            return _to_domain(row) if row is not None else None

    async def save(self, book: Book) -> None:
        """Insert a new book into the catalog."""
        row = BookRow(
            isbn=book.isbn.digits,
            title=book.title,
            author=book.author,
            genre=book.genre,
            description=book.description,
            available_stock=book.available_stock,
        )
        async with self._sessions() as session:
            session.add(row)
            await session.commit()

    async def count(self) -> int:
        """Return the total number of books in the catalog."""
        async with self._sessions() as session:
            result = await session.scalar(select(func.count()).select_from(BookRow))
            return int(result or 0)
