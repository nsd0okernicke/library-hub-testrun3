"""Domain exceptions for the loan service."""

from __future__ import annotations


class UserAlreadyExistsError(Exception):
    """Raised when creating a user whose email already exists."""

    def __init__(self, email: str) -> None:
        """Create the error, remembering the offending email."""
        super().__init__(f"user with email {email} already exists")
        self.email = email


class InvalidLoanListParametersError(ValueError):
    """Raised when a loan list request carries invalid pagination or user data."""


class UnknownUserError(Exception):
    """Raised when a borrow request names a user id that does not exist."""

    def __init__(self, user_id: str) -> None:
        """Create the error, remembering the offending user id."""
        super().__init__(f"user with id {user_id} does not exist")
        self.user_id = user_id
