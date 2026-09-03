"""Unit tests for the ISBN-13 value object."""

import dataclasses

import pytest

from catalog.domain.isbn import Isbn, IsbnValidationError


def test_valid_hyphenated_isbn() -> None:
    isbn = Isbn("978-0-14-103614-3")
    assert isbn.value == "978-0-14-103614-3"


def test_valid_plain_isbn() -> None:
    assert Isbn("9780141036143").value == "9780141036143"


def test_digits_property_strips_hyphens() -> None:
    assert Isbn("978-0-14-103614-3").digits == "9780141036143"


@pytest.mark.parametrize(
    "value",
    [
        "978-0-14-103614",  # 12 digits
        "978-0-14-103614-34",  # 14 digits
        "978-0-14-103614-X",  # letter
        "0-14-103614-3",  # ISBN-10 length
        "978--0-14-103614-3",  # double hyphen
        "-978-0-14-103614-3",  # leading hyphen
        "978-0-14-103614-3-",  # trailing hyphen
        "978 0 14 103614 3",  # spaces instead of hyphens
        "",  # empty
        "978-0-14-10361.3",  # non-digit character
    ],
)
def test_invalid_formats_raise(value: str) -> None:
    with pytest.raises(IsbnValidationError):
        Isbn(value)


def test_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        Isbn("not-an-isbn")


def test_isbn_is_immutable() -> None:
    isbn = Isbn("978-0-14-103614-3")
    with pytest.raises(dataclasses.FrozenInstanceError):
        isbn.value = "9780141036143"


def test_isbn_uses_slots() -> None:
    assert not hasattr(Isbn("978-0-14-103614-3"), "__dict__")
