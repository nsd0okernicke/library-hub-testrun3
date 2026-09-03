"""Domain exceptions for the loan service."""

from __future__ import annotations


class UserAlreadyExistsError(Exception):
    """Raised when creating a user whose email already exists."""

    def __init__(self, email: str) -> None:
        """Create the error, remembering the offending email."""
        super().__init__(f"user with email {email} already exists")
        self.email = email
