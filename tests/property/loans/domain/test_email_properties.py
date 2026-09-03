"""Property tests for the Email value object."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from loans.domain.email import Email, EmailValidationError

_PARTS = st.text(
    alphabet=st.characters(blacklist_characters="@", min_codepoint=1), min_size=1, max_size=20
)


@given(local=_PARTS, domain=_PARTS)
def test_well_formed_addresses_are_accepted(local: str, domain: str) -> None:
    """Any non-empty local part, single @ and non-empty domain is valid."""
    value = f"{local}@{domain}"
    email = Email(value)
    assert email.value == value


@given(local=_PARTS, domain=_PARTS)
def test_re_validation_round_trips(local: str, domain: str) -> None:
    """Re-validating a stored value is stable and preserves identity."""
    value = f"{local}@{domain}"
    assert Email(Email(value).value) == Email(value)


@given(st.text(min_size=0, max_size=25).filter(lambda s: "@" not in s))
def test_missing_separator_is_rejected(value: str) -> None:
    """A string without an @ sign has no local part/domain split."""
    with pytest.raises(EmailValidationError):
        Email(value)


@given(left=_PARTS, middle=_PARTS, right=_PARTS)
def test_two_separators_are_rejected(left: str, middle: str, right: str) -> None:
    """More than one @ sign is not 'an @ sign' plus a domain."""
    with pytest.raises(EmailValidationError):
        Email(f"{left}@{middle}@{right}")


@given(domain=_PARTS)
def test_missing_local_part_is_rejected(domain: str) -> None:
    """A leading @ has no local part."""
    with pytest.raises(EmailValidationError):
        Email(f"@{domain}")


@given(local=_PARTS)
def test_missing_domain_is_rejected(local: str) -> None:
    """A trailing @ has no domain."""
    with pytest.raises(EmailValidationError):
        Email(f"{local}@")
