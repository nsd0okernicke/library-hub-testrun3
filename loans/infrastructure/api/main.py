"""FastAPI application factory for the loan service."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from loans.application.borrow_book import BorrowBook
from loans.application.create_user import CreateUser
from loans.application.return_book import ReturnBook
from loans.application.settle_reservation import FulfillReservation, RejectReservation
from loans.application.view_user_loans import ViewUserLoans
from loans.domain.email import EmailValidationError
from loans.domain.exceptions import (
    InvalidLoanListParametersError,
    UnknownUserError,
    UserAlreadyExistsError,
)
from loans.domain.isbn import IsbnValidationError
from loans.domain.loan import (
    InvalidLoanDataError,
    LoanNotActiveError,
    LoanNotFoundError,
    LoanNotPendingError,
)
from loans.domain.ports import DomainEventPublisher, LoanRepository, UserRepository
from loans.domain.user import InvalidUserDataError
from loans.infrastructure.api.routers.loans import router as loans_router
from loans.infrastructure.api.routers.users import router as users_router
from loans.infrastructure.db.loan_repository import SqlAlchemyLoanRepository
from loans.infrastructure.db.models import Base
from loans.infrastructure.db.user_repository import SqlAlchemyUserRepository
from loans.infrastructure.events import InMemoryEventPublisher

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/loan_db"


def create_app(
    users: UserRepository,
    loans: LoanRepository,
    publisher: DomainEventPublisher | None = None,
) -> FastAPI:
    """Build the loan service FastAPI app wired to the given ports."""
    app = FastAPI(title="Loan Service")
    app.state.publisher = publisher or InMemoryEventPublisher()
    app.state.create_user = CreateUser(users)
    app.state.borrow_book = BorrowBook(users, loans)
    app.state.fulfill_reservation = FulfillReservation(loans)
    app.state.reject_reservation = RejectReservation(loans)
    app.state.view_user_loans = ViewUserLoans(users, loans)
    app.state.return_book = ReturnBook(loans, app.state.publisher)
    app.state.loan_repository = loans
    app.include_router(users_router)
    app.include_router(loans_router)

    async def conflict_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map a duplicate email, a settled loan or a non-ACTIVE return to 409."""
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map a missing user or loan to 404."""
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
        """Map invalid data to 400."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.add_exception_handler(UserAlreadyExistsError, conflict_handler)
    app.add_exception_handler(LoanNotPendingError, conflict_handler)
    app.add_exception_handler(LoanNotActiveError, conflict_handler)
    app.add_exception_handler(UnknownUserError, not_found_handler)
    app.add_exception_handler(LoanNotFoundError, not_found_handler)
    app.add_exception_handler(EmailValidationError, bad_request_handler)
    app.add_exception_handler(IsbnValidationError, bad_request_handler)
    app.add_exception_handler(InvalidUserDataError, bad_request_handler)
    app.add_exception_handler(InvalidLoanDataError, bad_request_handler)
    app.add_exception_handler(InvalidLoanListParametersError, bad_request_handler)
    return app


def build_default_app() -> FastAPI:
    """Build the app with SQLAlchemy repositories for local runs.

    The database URL can be overridden with the LOANS_DATABASE_URL
    environment variable.
    """
    url = os.environ.get("LOANS_DATABASE_URL", _DEFAULT_DATABASE_URL)
    engine = create_async_engine(url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def init_schema() -> None:
        """Create loan service tables on startup."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        """Close the engine on shutdown."""
        await engine.dispose()

    app = create_app(SqlAlchemyUserRepository(sessions), SqlAlchemyLoanRepository(sessions))

    @app.on_event("startup")
    async def _startup() -> None:
        await init_schema()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    return app


app = build_default_app()
