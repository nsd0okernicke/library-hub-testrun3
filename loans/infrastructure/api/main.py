"""FastAPI application factory for the loan service."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from loans.application.create_user import CreateUser
from loans.domain.email import EmailValidationError
from loans.domain.exceptions import UserAlreadyExistsError
from loans.domain.ports import UserRepository
from loans.domain.user import InvalidUserDataError
from loans.infrastructure.api.routers.users import router as users_router
from loans.infrastructure.db.models import Base
from loans.infrastructure.db.user_repository import SqlAlchemyUserRepository

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/loan_db"


def create_app(users: UserRepository) -> FastAPI:
    """Build the loan service FastAPI app wired to the given repository port."""
    app = FastAPI(title="Loan Service")
    app.state.create_user = CreateUser(users)
    app.include_router(users_router)

    async def conflict_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map a duplicate-email conflict to 409."""
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map invalid user data to 400."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.add_exception_handler(UserAlreadyExistsError, conflict_handler)
    app.add_exception_handler(EmailValidationError, bad_request_handler)
    app.add_exception_handler(InvalidUserDataError, bad_request_handler)
    return app


def build_default_app() -> FastAPI:
    """Build the app with a SQLAlchemy repository for local runs.

    The database URL can be overridden with the LOANS_DATABASE_URL
    environment variable.
    """
    url = os.environ.get("LOANS_DATABASE_URL", _DEFAULT_DATABASE_URL)
    engine = create_async_engine(url, poolclass=NullPool)

    async def init_schema() -> None:
        """Create loan service tables on startup."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        """Close the engine on shutdown."""
        await engine.dispose()

    app = create_app(SqlAlchemyUserRepository(async_sessionmaker(engine)))

    @app.on_event("startup")
    async def _startup() -> None:
        await init_schema()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    return app


app = build_default_app()
