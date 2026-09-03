"""Unit tests for the CreateUser use case with a fake repository port."""

import dataclasses

import pytest

from loans.application.create_user import CreateUser, CreateUserCommand
from loans.domain.email import EmailValidationError
from loans.domain.exceptions import UserAlreadyExistsError
from loans.domain.user import InvalidUserDataError
from tests.unit.loans.fakes import InMemoryUsers


def command(**overrides: object) -> CreateUserCommand:
    """Build a valid CreateUserCommand, applying keyword overrides."""
    values: dict[str, object] = {"name": "Anna Schmidt", "email": "anna.schmidt@example.com"}
    values.update(overrides)
    return CreateUserCommand(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_creates_user_and_persists_it() -> None:
    repo = InMemoryUsers()
    user = await CreateUser(repo).execute(command())

    assert user.name == "Anna Schmidt"
    assert user.email.value == "anna.schmidt@example.com"
    assert user.user_id
    assert list(repo.users.values())[0] is user


@pytest.mark.asyncio
async def test_two_creations_get_different_user_ids() -> None:
    repo = InMemoryUsers()
    use_case = CreateUser(repo)
    first = await use_case.execute(command())
    second = await use_case.execute(command(email="ben.mueller@example.com"))

    assert first.user_id != second.user_id


@pytest.mark.asyncio
async def test_custom_id_factory_is_used() -> None:
    repo = InMemoryUsers()
    use_case = CreateUser(repo, id_factory=lambda: "fixed-id")
    user = await use_case.execute(command())
    assert user.user_id == "fixed-id"


@pytest.mark.asyncio
async def test_existing_email_raises_conflict() -> None:
    repo = InMemoryUsers()
    use_case = CreateUser(repo)
    await use_case.execute(command())

    with pytest.raises(UserAlreadyExistsError):
        await use_case.execute(command())
    assert await repo.count() == 1


@pytest.mark.asyncio
async def test_invalid_email_format_rejected() -> None:
    repo = InMemoryUsers()
    with pytest.raises(EmailValidationError):
        await CreateUser(repo).execute(command(email="plainaddress"))
    assert await repo.count() == 0


@pytest.mark.parametrize("overrides", [{"name": ""}, {"name": None}])
@pytest.mark.asyncio
async def test_missing_name_rejected(overrides: dict[str, object]) -> None:
    repo = InMemoryUsers()
    with pytest.raises(InvalidUserDataError):
        await CreateUser(repo).execute(command(**overrides))
    assert await repo.count() == 0


def test_command_is_immutable() -> None:
    cmd = command()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.name = "Tampered"
