"""Unit tests for the Isbn value object of the loan service."""

import pytest

from loans.domain.isbn import Isbn, IsbnValidationError


@pytest.mark.parametrize(
    "value",
    [
        "9780201633610",
        "978-0-20-163361-0",
        "978-0-13-468599-1",
        "978-1-861000-92-1",
    ],
)
def test_valid_isbn_formats_are_accepted(value: str) -> None:
    """13 digits with hyphens allowed between them validate."""
    assert Isbn(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "978-0-14-103614",  # 12 digits
        "978-0-14-103614-34",  # 14 digits
        "978-0-14-103614-X",  # a letter
        "978--0-20-163361-0",  # double hyphen
        "-978-0-20-163361-0",  # leading hyphen
        "978-0-20-163361-0-",  # trailing hyphen
    ],
)
def test_invalid_isbn_formats_are_rejected(value: str) -> None:
    """Anything but exactly 13 digits with single hyphens fails."""
    with pytest.raises(IsbnValidationError):
        Isbn(value)


def test_digits_property_strips_hyphens() -> None:
    """The 13 digits are exposed without any hyphens."""
    assert Isbn("978-0-20-163361-0").digits == "9780201633610"


def test_isbn_is_immutable() -> None:
    """The value object carries no mutable state."""
    with pytest.raises(AttributeError):
        Isbn("978-0-20-163361-0").value = "978-0-13-468599-1"  # type: ignore[misc]
