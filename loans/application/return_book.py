"""Return-book use case for the loan service."""

from __future__ import annotations

from loans.domain.events import BookReturned
from loans.domain.loan import Loan, LoanNotFoundError
from loans.domain.ports import DomainEventPublisher, LoanRepository


class ReturnBook:
    """Closes an ACTIVE loan and publishes a BookReturned event.

    Only loans in status ACTIVE may be returned; any other status raises
    ``LoanNotActiveError`` and leaves the loan unchanged, with no event
    published. A loan id that names no stored loan raises
    ``LoanNotFoundError``. There is no penalty or overdue check: a loan
    returned after its due date closes exactly like an on-time one.
    """

    def __init__(self, loans: LoanRepository, publisher: DomainEventPublisher) -> None:
        """Bind the use case to its ports."""
        self._loans = loans
        self._publisher = publisher

    async def execute(self, loan_id: str) -> Loan:
        """Mark the loan named by the loan id as RETURNED and publish the event."""
        loan = await self._loans.get(loan_id)
        if loan is None:
            raise LoanNotFoundError(loan_id)
        loan.mark_returned()
        await self._loans.save(loan)
        await self._publisher.publish(
            BookReturned(loan_id=loan.loan_id, user_id=loan.user_id, isbn=loan.isbn)
        )
        return loan
