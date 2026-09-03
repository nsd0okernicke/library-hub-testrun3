"""Unit tests for the User entity (pure Python, no I/O)."""

import pytest

from loans.domain.email import Email
from loans.domain.user import InvalidUserDataError, User


def make_user(**overrides: object) -> User:
    """Build a valid User, applying keyword overrides."""
    values: dict[str, object] = {
        "user_id": "u-1",
        "name": "Anna Schmidt",
        "email": Email("anna.schmidt@example.com"),
    }
    values.update(overrides)
    return User(**values)  # type: ignore[arg-type]


def test_user_holds_identity_name_and_email() -> None:
    user = make_user()
    assert user.user_id == "u-1"
    assert user.name == "Anna Schmidt"
    assert user.email.value == "anna.schmidt@example.com"


@pytest.mark.parametrize("overrides", [{"name": ""}, {"user_id": ""}])
def test_user_rejects_empty_required_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidUserDataError):
        make_user(**overrides)


def test_user_rejects_unknown_attributes() -> None:
    """User carries exactly its identity fields; no stray state may accumulate."""
    user = make_user()
    with pytest.raises(AttributeError):
        user.phone = "012345"
