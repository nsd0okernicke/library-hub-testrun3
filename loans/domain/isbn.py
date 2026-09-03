"""ISBN-13 value object with format validation for the loan service.

The format rules mirror book creation in the catalog service: exactly 13
digits with hyphens allowed between the digits, no check-digit validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Exactly 13 digits with optional single hyphens between the digits.
_ISBN13_PATTERN = re.compile(r"\d(?:-?\d){12}\Z")


class IsbnValidationError(ValueError):
    """Raised when a string is not a valid ISBN-13 format."""


@dataclass(frozen=True, slots=True)
class Isbn:
    """A validated ISBN-13.

    A valid value consists of exactly 13 digits, with hyphens allowed between
    the digits. No check-digit validation is applied.
    """

    value: str

    def __post_init__(self) -> None:
        if not _ISBN13_PATTERN.fullmatch(self.value):
            raise IsbnValidationError(f"invalid ISBN-13 format: {self.value!r}")

    @property
    def digits(self) -> str:
        """The 13 digits of the ISBN with all hyphens removed."""
        return self.value.replace("-", "")
