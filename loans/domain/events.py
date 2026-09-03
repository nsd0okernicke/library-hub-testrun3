"""Domain events for the loan service."""

from __future__ import annotations

from dataclasses import dataclass

from loans.domain.isbn import Isbn


class DomainEvent:
    """Base class for domain events of the loan service."""


@dataclass(frozen=True)
class BookReturned(DomainEvent):
    """Published when an ACTIVE loan is closed by a return.

    Carries the loan id, the user id and the isbn of the returned book.
    """

    loan_id: str
    user_id: str
    isbn: Isbn
