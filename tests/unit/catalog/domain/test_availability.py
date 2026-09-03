"""Unit tests for the AvailabilityStatus value object."""

from __future__ import annotations

import dataclasses

import pytest

from catalog.domain.availability import AvailabilityStatus, InvalidAvailabilityError


def test_availability_status_holds_isbn_and_count() -> None:
    """A status value records the ISBN and its available count."""
    status = AvailabilityStatus(isbn="978-0-14-103614-3", available_count=5)

    assert status.isbn == "978-0-14-103614-3"
    assert status.available_count == 5


def test_availability_status_with_zero_count_is_valid() -> None:
    """A count of zero is a valid availability state (out of stock)."""
    status = AvailabilityStatus(isbn="978-0-06-112008-4", available_count=0)

    assert status.available_count == 0


def test_availability_status_rejects_negative_count() -> None:
    """A negative available count violates the availability invariant."""
    with pytest.raises(InvalidAvailabilityError):
        AvailabilityStatus(isbn="978-0-14-103614-3", available_count=-1)


def test_availability_status_is_immutable() -> None:
    """The status value cannot be mutated after construction."""
    status = AvailabilityStatus(isbn="978-0-14-103614-3", available_count=5)

    with pytest.raises(dataclasses.FrozenInstanceError):
        status.available_count = 6  # type: ignore[misc]
