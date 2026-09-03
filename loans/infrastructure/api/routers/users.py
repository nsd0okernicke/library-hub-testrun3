"""HTTP routes for user accounts in the loan service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from loans.application.create_user import CreateUser, CreateUserCommand
from loans.domain.user import User
from loans.infrastructure.api.schemas import UserCreateRequest

router = APIRouter()


def _user_payload(user: User) -> dict[str, object]:
    """Shape a User into its HTTP response representation."""
    return {"user_id": user.user_id, "name": user.name, "email": user.email.value}


@router.post("/users", status_code=201)
async def create_user(payload: UserCreateRequest, request: Request) -> dict[str, object]:
    """Create a new user account and return it including its system id."""
    command = CreateUserCommand(name=payload.name, email=payload.email)
    use_case: CreateUser = request.app.state.create_user
    user = await use_case.execute(command)
    return _user_payload(user)
