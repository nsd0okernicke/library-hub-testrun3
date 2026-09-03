"""Reservation settlement use cases for the loan service."""

from __future__ import annotations

from collections.abc import Callable

from loans.domain.loan import Loan, LoanNotFoundError
from loans.domain.ports import LoanRepository


async def _settle(loans: LoanRepository, loan_id: str, settle: Callable[[Loan], None]) -> Loan:
    """Load the loan, apply the reservation outcome and persist the result."""
    loan = await loans.get(loan_id)
    if loan is None:
        raise LoanNotFoundError(loan_id)
    settle(loan)
    await loans.save(loan)
    return loan


class FulfillReservation:
    """Applies a fulfilled reservation: the loan becomes ACTIVE with a due date."""

    def __init__(self, loans: LoanRepository) -> None:
        """Bind the use case to the LoanRepository port."""
        self._loans = loans

    async def execute(self, loan_id: str) -> Loan:
        """Activate the loan named by the loan id."""
        return await _settle(self._loans, loan_id, Loan.fulfill)


class RejectReservation:
    """Applies a rejected reservation: the loan stays queryable in REJECTED."""

    def __init__(self, loans: LoanRepository) -> None:
        """Bind the use case to the LoanRepository port."""
        self._loans = loans

    async def execute(self, loan_id: str) -> Loan:
        """Mark the loan named by the loan id as rejected."""
        return await _settle(self._loans, loan_id, Loan.reject)
