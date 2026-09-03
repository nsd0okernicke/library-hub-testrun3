"""Property tests for the ISBN-13 value object."""

from __future__ import annotations

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from catalog.domain.isbn import Isbn, IsbnValidationError

_VALID = re.compile(r"\d(?:-?\d){12}\Z")


@given(st.from_regex(r"\d(?:-?\d){12}", fullmatch=True))
def test_every_13_digit_hyphenation_is_accepted(value: str) -> None:
    """Any string of exactly 13 digits with hyphens between digits is valid."""
    isbn = Isbn(value)
    assert isbn.value == value
    assert len(isbn.digits) == 13
    assert isbn.digits == value.replace("-", "")


@given(
    st.text(
        alphabet=st.characters(whitelist_categories=("Nd", "L", "P", "Z", "S")),
        min_size=0,
        max_size=25,
    ).filter(lambda s: not _VALID.match(s))
)
def test_everything_else_is_rejected(value: str) -> None:
    """Any other string is rejected with an IsbnValidationError."""
    with pytest.raises(IsbnValidationError):
        Isbn(value)


@given(st.from_regex(r"\d(?:-?\d){12}", fullmatch=True))
def test_digits_is_idempotent(value: str) -> None:
    """Re-validating the digit string succeeds and is stable."""
    isbn = Isbn(value)
    plain = Isbn(isbn.digits)
    assert plain.digits == isbn.digits
