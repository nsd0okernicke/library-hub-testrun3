"""Acceptance fixtures: Testcontainers PostgreSQL behind the catalog app.

A NullPool engine is used so each request opens a fresh connection in the
event loop that serves it; the synchronous TestClient runs the async app in
its own portal loop, and pooled connections are not loop-reentrant.
"""

from __future__ import annotations

from collections import namedtuple
from collections.abc import Generator

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from catalog.infrastructure.api.main import create_app
from catalog.infrastructure.db.book_repository import SqlAlchemyBookRepository
from catalog.infrastructure.db.models import Base

Catalog = namedtuple("Catalog", ["client", "repository"])


class StepContext:
    """Mutable bag of values shared by the steps of one scenario."""


@pytest.fixture()
def context() -> StepContext:
    """Per-scenario context shared by the pytest-bdd steps."""
    return StepContext()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Session-scoped PostgreSQL container shared by all scenarios."""
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

    repository = SqlAlchemyBookRepository(async_sessionmaker(engine, expire_on_commit=False))
    app = create_app(repository)
    with TestClient(app) as client:
        yield Catalog(client=client, repository=repository)
    await engine.dispose()
