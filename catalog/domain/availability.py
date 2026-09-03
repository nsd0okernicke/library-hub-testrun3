"""Availability value object for the catalog service."""

from __future__ import annotations

from dataclasses import dataclass


class InvalidAvailabilityError(ValueError):
    """Raised when an availability report violates catalog rules."""


@dataclass(frozen=True, slots=True)
class AvailabilityStatus:
    """The current availability of one book: its ISBN and available count.

    Deliberately carries no other book metadata so consumers can run a cheap
    availability check without retrieving full metadata.
    """

    isbn: str
    available_count: int

    def __post_init__(self) -> None:
        if self.available_count < 0:
            raise InvalidAvailabilityError("available_count must be >= 0")
