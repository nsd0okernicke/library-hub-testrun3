"""Acceptance fixtures: Testcontainers PostgreSQL behind the catalog app.

A NullPool engine is used so each request opens a fresh connection in the
event loop that serves it; the synchronous TestClient runs the async app in
its own portal loop, and pooled connections are not loop-reentrant.
"""

from __future__ import annotations

from collections import namedtuple
from collections.abc import Generator
from typing import Any

import pytest
from pytest_bdd import then
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from catalog.infrastructure.api.main import create_app
from catalog.infrastructure.db.book_repository import SqlAlchemyBookRepository
from catalog.infrastructure.db.models import Base
from loans.infrastructure.api.main import create_app as create_loan_app
from loans.infrastructure.db.loan_repository import SqlAlchemyLoanRepository
from loans.infrastructure.db.models import Base as LoanBase
from loans.infrastructure.db.user_repository import SqlAlchemyUserRepository

Catalog = namedtuple("Catalog", ["client", "repository", "session_factory"])
Loans = namedtuple("Loans", ["client", "repository", "loan_repository"])


class StepContext:
    """Mutable bag of values shared by the steps of one scenario."""


@pytest.fixture()
def context() -> StepContext:
    """Per-scenario context shared by the pytest-bdd steps."""
    return StepContext()


# Generic HTTP status steps shared by all service step modules.
# pytest-bdd registers steps per module, so cross-service steps live here.


@then("the request succeeds with a 201 Created")
def request_succeeded(context: Any) -> None:
    """Assert the last request returned 201 Created."""
    assert context.response.status_code == 201, context.response.text


@then("the request is rejected with a 409 Conflict")
def request_conflict(context: Any) -> None:
    """Assert the last request returned 409 Conflict."""
    assert context.response.status_code == 409, context.response.text


@then("the request is rejected with a 400 Bad Request")
def request_bad_request(context: Any) -> None:
    """Assert the last request returned 400 Bad Request."""
    assert context.response.status_code == 400, context.response.text


@then("the request succeeds with a 202 Accepted")
def request_accepted(context: Any) -> None:
    """Assert the last request returned 202 Accepted."""
    assert context.response.status_code == 202, context.response.text


@then("the request succeeds with a 200 OK")
def request_ok(context: Any) -> None:
    """Assert the last request returned 200 OK."""
    assert context.response.status_code == 200, context.response.text


@then("the request is rejected with a 404 Not Found")
def request_not_found(context: Any) -> None:
    """Assert the last request returned 404 Not Found."""
    assert context.response.status_code == 404, context.response.text


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Session-scoped PostgreSQL container shared by all scenarios."""
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def loans_postgres_container() -> Generator[PostgresContainer, None, None]:
    """Session-scoped PostgreSQL container for the loan service scenarios."""
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture()
async def catalog(postgres_container: PostgresContainer) -> Generator[Catalog, None, None]:
    """Function-scoped catalog app with a freshly created, empty books table."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    url = (
        f"postgresql+asyncpg://{postgres_container.username}:"
        f"{postgres_container.password}@{host}:{port}/{postgres_container.dbname}"
    )
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(Base.metadata.tables["books"].delete())

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlAlchemyBookRepository(sessions)
    app = create_app(repository)
    with TestClient(app) as client:
        yield Catalog(client=client, repository=repository, session_factory=sessions)
    await engine.dispose()


@pytest.fixture()
async def loans(loans_postgres_container: PostgresContainer) -> Generator[Loans, None, None]:
    """Function-scoped loan app with freshly created, empty users and loans tables."""
    host = loans_postgres_container.get_container_host_ip()
    port = loans_postgres_container.get_exposed_port(5432)
    url = (
        f"postgresql+asyncpg://{loans_postgres_container.username}:"
        f"{loans_postgres_container.password}@{host}:{port}/{loans_postgres_container.dbname}"
    )
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(LoanBase.metadata.create_all)
        await conn.execute(LoanBase.metadata.tables["users"].delete())
        await conn.execute(LoanBase.metadata.tables["loans"].delete())

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    users_repository = SqlAlchemyUserRepository(sessions)
    loan_repository = SqlAlchemyLoanRepository(sessions)
    app = create_loan_app(users_repository, loan_repository)
    with TestClient(app) as client:
        yield Loans(client=client, repository=users_repository, loan_repository=loan_repository)
    await engine.dispose()
