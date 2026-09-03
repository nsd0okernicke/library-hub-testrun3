"""Pydantic DTOs for the loan service HTTP API."""

from __future__ import annotations

from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    """Payload for POST /users.

    Fields default to empty so that missing data surfaces as a 400 from the
    domain layer rather than a 422 from the HTTP layer. The client never
    provides the user id; the system generates it.
    """

    name: str = ""
    email: str = ""


class LoanCreateRequest(BaseModel):
    """Payload for POST /loans.

    Fields default to empty so that missing data surfaces as a 400 from the
    domain layer rather than a 422 from the HTTP layer. The client never
    provides the loan id; the system generates it.
    """

    user_id: str = ""
    isbn: str = ""
