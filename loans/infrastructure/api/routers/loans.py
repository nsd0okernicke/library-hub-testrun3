"""HTTP routes for loans in the loan service."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from loans.application.borrow_book import BorrowBook, BorrowBookCommand
from loans.application.settle_reservation import FulfillReservation, RejectReservation
from loans.application.view_user_loans import ViewUserLoans
from loans.domain.loan import Loan, LoanNotFoundError
from loans.domain.loan_list import LoanListQuery
from loans.infrastructure.api.schemas import LoanCreateRequest

router = APIRouter()


def _loan_payload(loan: Loan) -> dict[str, object]:
    """Shape a Loan into its HTTP response representation."""
    return {
        "loan_id": loan.loan_id,
        "user_id": loan.user_id,
        "isbn": loan.isbn.value,
        "status": loan.status.value,
        "due_date": loan.due_date.isoformat() if loan.due_date is not None else None,
        "created_at": loan.requested_on.isoformat(),
    }


@router.post("/loans", status_code=202)
async def borrow_book(payload: LoanCreateRequest, request: Request) -> dict[str, object]:
    """Register a borrow request as a PENDING loan.

    Stock reservation happens later, out of band; the 202 answers the
    request as soon as the loan record exists.
    """
    command = BorrowBookCommand(user_id=payload.user_id, isbn=payload.isbn)
    use_case: BorrowBook = request.app.state.borrow_book
    loan = await use_case.execute(command)
    return _loan_payload(loan)


@router.get("/loans/{loan_id}")
async def get_loan(loan_id: str, request: Request) -> dict[str, object]:
    """Return the loan record for the loan id."""
    loan = await request.app.state.loan_repository.get(loan_id)
    if loan is None:
        raise LoanNotFoundError(loan_id)
    return _loan_payload(loan)


@router.get("/users/{user_id}/loans")
async def view_user_loans(
    user_id: str,
    request: Request,
    page: int = Query(default=1),
    page_size: int = Query(default=20),
) -> dict[str, object]:
    """Return one page of the user's loans, newest first.

    All four statuses appear; ``total`` counts every loan of the user, not
    only this page. A user id naming no account is a 404; ``page`` and
    ``page_size`` outside their valid range are 400 Bad Request.
    """
    use_case: ViewUserLoans = request.app.state.view_user_loans
    result = await use_case.execute(LoanListQuery(user_id=user_id, page=page, page_size=page_size))
    return {
        "items": [_loan_payload(loan) for loan in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.post("/loans/{loan_id}/reservation/fulfilled")
async def reservation_fulfilled(loan_id: str, request: Request) -> dict[str, object]:
    """Apply a fulfilled reservation: the loan becomes ACTIVE with a due date."""
    use_case: FulfillReservation = request.app.state.fulfill_reservation
    loan = await use_case.execute(loan_id)
    return _loan_payload(loan)


@router.post("/loans/{loan_id}/reservation/rejected")
async def reservation_rejected(loan_id: str, request: Request) -> dict[str, object]:
    """Apply a rejected reservation: the loan stays queryable in REJECTED."""
    use_case: RejectReservation = request.app.state.reject_reservation
    loan = await use_case.execute(loan_id)
    return _loan_payload(loan)
