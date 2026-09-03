"""Property tests for the Book entity."""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from catalog.domain.book import Book, InvalidBookDataError
from catalog.domain.isbn import Isbn

ISBN = Isbn("978-0-14-103614-3")
text = st.text(min_size=1, max_size=50)


@given(title=text, author=text, genre=text, stock=st.integers(min_value=0, max_value=10_000))
def test_valid_fields_round_trip(title: str, author: str, genre: str, stock: int) -> None:
    """A Book built from valid fields stores them unchanged."""
    book = Book(isbn=ISBN, title=title, author=author, genre=genre, available_stock=stock)
    assert book.title == title
    assert book.author == author
    assert book.genre == genre
    assert book.available_stock == stock


@given(description=st.one_of(st.text(max_size=200), st.none()))
def test_description_none_normalises_to_empty(description: str | None) -> None:
    """A missing description is always stored as the empty string."""
    book = Book(
        isbn=ISBN,
        title="T",
        author="A",
        genre="G",
        available_stock=0,
        description=description,
    )
    assert book.description == (description or "")


@given(stock=st.integers(max_value=-1))
def test_negative_stock_is_rejected(stock: int) -> None:
    """Stock below zero is never accepted."""
    with pytest.raises(InvalidBookDataError):
        Book(isbn=ISBN, title="T", author="A", genre="G", available_stock=stock)


@given(title=st.text(max_size=50), author=st.text(max_size=50), genre=st.text(max_size=50))
def test_at_least_one_empty_required_field_is_rejected(title: str, author: str, genre: str) -> None:
    """If any of title/author/genre is empty, construction must fail."""
    assume(not (title and author and genre))
    with pytest.raises(InvalidBookDataError):
        Book(isbn=ISBN, title=title, author=author, genre=genre, available_stock=0)
