"""Email value object with format validation for the loan service."""

from __future__ import annotations

from dataclasses import dataclass


class EmailValidationError(ValueError):
    """Raised when a string is not a valid email address."""


@dataclass(frozen=True, slots=True)
class Email:
    """A validated email address: unique identity of a user account.

    A valid value consists of a non-empty local part, a single ``@`` sign
    and a non-empty domain.
    """

    value: str

    def __post_init__(self) -> None:
        local, separator, domain = self.value.partition("@")
        if separator != "@" or "@" in domain or not local or not domain:
            raise EmailValidationError(f"invalid email format: {self.value!r}")
