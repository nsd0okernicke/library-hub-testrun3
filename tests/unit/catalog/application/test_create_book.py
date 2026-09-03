"""Unit tests for the CreateBook use case with a fake repository port."""

import dataclasses

import pytest

from catalog.application.create_book import CreateBook, CreateBookCommand
from catalog.domain.book import InvalidBookDataError
from catalog.domain.exceptions import BookAlreadyExistsError
from catalog.domain.isbn import IsbnValidationError
from tests.unit.catalog.fakes import InMemoryBooks


def command(**overrides: object) -> CreateBookCommand:
    """Build a valid CreateBookCommand, applying keyword overrides."""
    values: dict[str, object] = {
        "isbn": "978-0-14-103614-3",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "genre": "Fiction",
        "initial_stock": 5,
        "description": "",
    }
    values.update(overrides)
    return CreateBookCommand(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_creates_book_and_persists_it() -> None:
    repo = InMemoryBooks()
    use_case = CreateBook(repo)
    book = await use_case.execute(command())

    assert book.title == "The Great Gatsby"
    assert book.available_stock == 5
    assert repo.books["9780141036143"] is book


@pytest.mark.asyncio
async def test_default_description_is_empty_string() -> None:
    repo = InMemoryBooks()
    book = await CreateBook(repo).execute(command(description=None))
    assert book.description == ""


@pytest.mark.asyncio
async def test_existing_isbn_raises_conflict() -> None:
    repo = InMemoryBooks()
    use_case = CreateBook(repo)
    await use_case.execute(command())

    with pytest.raises(BookAlreadyExistsError):
        await use_case.execute(command())
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_invalid_isbn_format_rejected() -> None:
    repo = InMemoryBooks()
    with pytest.raises(IsbnValidationError):
        await CreateBook(repo).execute(command(isbn="978-0-14-103614"))
    assert await repo.count() == 0


@pytest.mark.asyncio
async def test_isbn_uniqueness_ignores_hyphenation() -> None:
    repo = InMemoryBooks()
    use_case = CreateBook(repo)
    await use_case.execute(command(isbn="978-0-14-103614-3"))

    with pytest.raises(BookAlreadyExistsError):
        await use_case.execute(command(isbn="9780141036143"))


@pytest.mark.parametrize("overrides", [{"title": ""}, {"author": ""}, {"genre": ""}])
@pytest.mark.asyncio
async def test_missing_required_data_rejected(overrides: dict[str, object]) -> None:
    repo = InMemoryBooks()
    with pytest.raises(InvalidBookDataError):
        await CreateBook(repo).execute(command(**overrides))
    assert await repo.count() == 0


@pytest.mark.asyncio
async def test_negative_stock_rejected() -> None:
    repo = InMemoryBooks()
    with pytest.raises(InvalidBookDataError):
        await CreateBook(repo).execute(command(initial_stock=-1))
    assert await repo.count() == 0


def test_command_is_immutable() -> None:
    cmd = command()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.title = "Tampered"
