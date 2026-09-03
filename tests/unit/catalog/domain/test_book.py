"""Unit tests for the Book entity."""

import pytest

from catalog.domain.book import Book, InvalidBookDataError
from catalog.domain.isbn import Isbn

ISBN = Isbn("978-0-14-103614-3")


def make_book(**overrides: object) -> Book:
    """Build a valid Book, applying keyword overrides."""
    values: dict[str, object] = {
        "isbn": ISBN,
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "genre": "Fiction",
        "available_stock": 5,
        "description": "A novel",
    }
    values.update(overrides)
    return Book(**values)  # type: ignore[arg-type]


def test_valid_book_round_trips_fields() -> None:
    book = make_book()
    assert book.isbn == ISBN
    assert book.title == "The Great Gatsby"
    assert book.author == "F. Scott Fitzgerald"
    assert book.genre == "Fiction"
    assert book.available_stock == 5
    assert book.description == "A novel"


def test_zero_stock_is_valid() -> None:
    assert make_book(available_stock=0).available_stock == 0


@pytest.mark.parametrize("field", ["title", "author", "genre"])
def test_empty_required_fields_rejected(field: str) -> None:
    with pytest.raises(InvalidBookDataError):
        make_book(**{field: ""})


def test_negative_stock_rejected() -> None:
    with pytest.raises(InvalidBookDataError):
        make_book(available_stock=-1)


def test_none_description_stored_as_empty_string() -> None:
    book = make_book(description=None)
    assert book.description == ""


def test_invalid_book_data_error_is_value_error() -> None:
    with pytest.raises(ValueError):
        make_book(title="")


def test_book_uses_slots() -> None:
    assert not hasattr(make_book(), "__dict__")
