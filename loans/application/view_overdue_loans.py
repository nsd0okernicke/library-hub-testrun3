"""View-overdue-loans use case for the loan service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from loans.domain.loan import Loan
from loans.domain.ports import LoanRepository


class ViewOverdueLoans:
    """Returns every overdue loan, across all users, most overdue first.

    A loan is overdue when it is ACTIVE and its due date lies strictly
    before the current day; loans in any other status never appear. The
    result is sorted by due date ascending (most overdue first); loans
    sharing a due date are ordered by loan id for determinism. The current
    day is injected so the behavior stays testable.
    """

    def __init__(self, loans: LoanRepository, today: Callable[[], date] = date.today) -> None:
        """Bind the use case to the loan repository port and a day source."""
        self._loans = loans
        self._today = today

    async def execute(self) -> list[Loan]:
        """List every overdue loan, sorted by due date ascending."""
        active_loans = await self._loans.list_active()
        today = self._today()
        overdue: list[tuple[date, str, Loan]] = []
        for loan in active_loans:
            if loan.is_overdue(today) and loan.due_date is not None:
                overdue.append((loan.due_date, loan.loan_id, loan))
        overdue.sort()
        return [loan for _, _, loan in overdue]
