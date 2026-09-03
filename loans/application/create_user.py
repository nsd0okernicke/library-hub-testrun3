"""Create-user use case for the loan service."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from loans.domain.email import Email
from loans.domain.exceptions import UserAlreadyExistsError
from loans.domain.ports import UserRepository
from loans.domain.user import User


def _default_user_id() -> str:
    """Generate a system-unique user id."""
    return uuid.uuid4().hex


@dataclass(frozen=True)
class CreateUserCommand:
    """Input for the create-user use case.

    The system generates the user id; the command carries no id.
    """

    name: str = ""
    email: str = ""


class CreateUser:
    """Registers a new user account from a name and a unique email.

    Raises ``EmailValidationError`` for an invalid email format,
    ``InvalidUserDataError`` for a missing name, and
    ``UserAlreadyExistsError`` when the email is already an account.
    """

    def __init__(
        self, users: UserRepository, id_factory: Callable[[], str] = _default_user_id
    ) -> None:
        """Bind the use case to a UserRepository port and id generator."""
        self._users = users
        self._id_factory = id_factory

    async def execute(self, command: CreateUserCommand) -> User:
        """Create and persist the user described by the command."""
        email = Email(command.email)
        if await self._users.get_by_email(email) is not None:
            raise UserAlreadyExistsError(email.value)
        user = User(user_id=self._id_factory(), name=command.name or "", email=email)
        await self._users.save(user)
        return user
