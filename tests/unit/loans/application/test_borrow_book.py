"""Unit tests for the BorrowBook use case."""

from datetime import date

import pytest

from loans.application.borrow_book import BorrowBook, BorrowBookCommand
from loans.domain.email import Email
from loans.domain.exceptions import UnknownUserError
from loans.domain.isbn import IsbnValidationError
from loans.domain.loan import InvalidLoanDataError, LoanStatus
from loans.domain.user import User
from tests.unit.loans.fakes import InMemoryLoans, InMemoryUsers

REQUEST_DATE = date(2026, 9, 3)


@pytest.fixture()
async def users() -> tuple[InMemoryUsers, User]:
    """An account base holding one known user."""
    users = InMemoryUsers()
    user = User(user_id="user-1", name="Anna Schmidt", email=Email("a@example.com"))
    await users.save(user)
    return users, user


@pytest.fixture()
def loans() -> InMemoryLoans:
    """Fresh in-memory loan store."""
    return InMemoryLoans()


def make_use_case(users: InMemoryUsers, loans: InMemoryLoans) -> BorrowBook:
    """Wire the use case to the fakes with a fixed request date."""
    return BorrowBook(users, loans, date_factory=lambda: REQUEST_DATE)


async def test_borrow_creates_pending_loan(
    users: tuple[InMemoryUsers, User], loans: InMemoryLoans
) -> None:
    """A valid request yields a PENDING loan with a system-generated id."""
    users_repo, user = users
    created = await make_use_case(users_repo, loans).execute(
        BorrowBookCommand(user_id=user.user_id, isbn="978-0-20-163361-0")
    )

    assert created.status is LoanStatus.PENDING
    assert created.user_id == user.user_id
    assert created.due_date is None
    assert created.requested_on == REQUEST_DATE
    assert await loans.get(created.loan_id) is not None


async def test_loan_id_is_system_generated(
    users: tuple[InMemoryUsers, User], loans: InMemoryLoans
) -> None:
    """Two borrow requests for the same user get distinct loan ids."""
    users_repo, user = users
    use_case = make_use_case(users_repo, loans)
    command = BorrowBookCommand(user_id=user.user_id, isbn="978-0-20-163361-0")

    first = await use_case.execute(command)
    second = await use_case.execute(command)

    assert first.loan_id != second.loan_id


async def test_no_concurrent_loan_limit(
    users: tuple[InMemoryUsers, User], loans: InMemoryLoans
) -> None:
    """A user may hold several loans, even for the same isbn."""
    users_repo, user = users
    use_case = make_use_case(users_repo, loans)
    command = BorrowBookCommand(user_id=user.user_id, isbn="978-0-20-163361-0")

    for _ in range(3):
        await use_case.execute(command)

    assert await loans.count() == 3


async def test_unknown_user_is_rejected(
    users: tuple[InMemoryUsers, User], loans: InMemoryLoans
) -> None:
    """A borrow request for a missing user id fails and stores no loan."""
    users_repo, _ = users
    with pytest.raises(UnknownUserError):
        await make_use_case(users_repo, loans).execute(
            BorrowBookCommand(user_id="ghost", isbn="978-0-20-163361-0")
        )
    assert await loans.count() == 0


@pytest.mark.parametrize(
    "command_fields, expected_error",
    [
        ({"user_id": "", "isbn": "978-0-20-163361-0"}, InvalidLoanDataError),
        ({"user_id": "user-1", "isbn": ""}, IsbnValidationError),
        ({"user_id": "user-1", "isbn": "978-0-14-103614"}, IsbnValidationError),  # 12 digits
        ({"user_id": "user-1", "isbn": "978-0-14-103614-34"}, IsbnValidationError),  # 14 digits
        ({"user_id": "user-1", "isbn": "978-0-14-103614-X"}, IsbnValidationError),  # letter
    ],
)
async def test_invalid_request_is_rejected_without_loan(
    users: tuple[InMemoryUsers, User],
    loans: InMemoryLoans,
    command_fields: dict[str, str],
    expected_error: type[Exception],
) -> None:
    """Missing or malformed data raises and stores no loan."""
    users_repo, _ = users
    with pytest.raises(expected_error):
        await make_use_case(users_repo, loans).execute(
            BorrowBookCommand(**command_fields)  # type: ignore[arg-type]
        )
    assert await loans.count() == 0
