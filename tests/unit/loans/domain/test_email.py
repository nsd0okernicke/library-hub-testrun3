"""Unit tests for the Email value object (pure Python, no I/O)."""

import pytest

from loans.domain.email import Email, EmailValidationError


@pytest.mark.parametrize(
    "value",
    [
        "anna.schmidt@example.com",
        "ben@mueller.example",
        "first.last@sub.domain.org",
        "a@b",
    ],
)
def test_valid_emails_are_accepted(value: str) -> None:
    assert Email(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "plainaddress",
        "@example.com",
        "user@",
        "a@b@c",
    ],
)
def test_invalid_emails_are_rejected(value: str) -> None:
    with pytest.raises(EmailValidationError):
        Email(value)


def test_invalid_email_message_names_the_offending_value() -> None:
    with pytest.raises(EmailValidationError, match="plainaddress"):
        Email("plainaddress")
