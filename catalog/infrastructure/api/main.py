"""FastAPI application factory for the catalog service."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from catalog.application.check_book_availability import CheckBookAvailability
from catalog.application.create_book import CreateBook
from catalog.application.handle_book_returned import HandleBookReturnedEvent
from catalog.application.retrieve_book import RetrieveBook
from catalog.application.search_books import SearchBooks
from catalog.domain.book import InvalidBookDataError
from catalog.domain.exceptions import (
    BookAlreadyExistsError,
    BookNotFoundError,
    InvalidSearchParametersError,
)
from catalog.domain.isbn import IsbnValidationError
from catalog.domain.ports import BookRepository
from catalog.infrastructure.api.routers.books import router as books_router
from catalog.infrastructure.db.book_repository import SqlAlchemyBookRepository
from catalog.infrastructure.db.models import Base

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/catalog_db"


def create_app(books: BookRepository) -> FastAPI:
    """Build the catalog FastAPI app wired to the given repository port."""
    app = FastAPI(title="Catalog Service")
    app.state.create_book = CreateBook(books)
    app.state.check_book_availability = CheckBookAvailability(books)
    app.state.retrieve_book = RetrieveBook(books)
    app.state.search_books = SearchBooks(books)
    app.state.handle_book_returned = HandleBookReturnedEvent(books)
    app.include_router(books_router)

    async def conflict_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map a duplicate-ISBN conflict to 409."""
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map a missing book to 404."""
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map invalid book data to 400."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.add_exception_handler(BookAlreadyExistsError, conflict_handler)
    app.add_exception_handler(BookNotFoundError, not_found_handler)
    app.add_exception_handler(IsbnValidationError, bad_request_handler)
    app.add_exception_handler(InvalidBookDataError, bad_request_handler)
    app.add_exception_handler(InvalidSearchParametersError, bad_request_handler)
    return app


def build_default_app() -> FastAPI:
    """Build the app with a SQLAlchemy repository for local runs.

    The database URL can be overridden with the CATALOG_DATABASE_URL
    environment variable.
    """
    url = os.environ.get("CATALOG_DATABASE_URL", _DEFAULT_DATABASE_URL)
    engine = create_async_engine(url, poolclass=NullPool)

    async def init_schema() -> None:
        """Create catalog tables on startup."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        """Close the engine on shutdown."""
        await engine.dispose()

    app = create_app(SqlAlchemyBookRepository(async_sessionmaker(engine)))

    @app.on_event("startup")
    async def _startup() -> None:
        await init_schema()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    return app


app = build_default_app()
