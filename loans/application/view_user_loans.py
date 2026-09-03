"""View-user-loans use case for the loan service."""

from __future__ import annotations

from loans.domain.exceptions import UnknownUserError
from loans.domain.loan_list import LoanListQuery, LoanListResult
from loans.domain.ports import LoanRepository, UserRepository


class ViewUserLoans:
    """Returns one page of a single user's loans, newest first.

    The user must exist; a user id naming no account raises
    ``UnknownUserError``. Every loan of the user appears regardless of
    status (PENDING, ACTIVE, REJECTED, RETURNED are all queryable), sorted
    by creation date descending, then loan id ascending for determinism,
    and sliced into the requested page. The total counts every loan of the
    user, not only the current page.
    """

    def __init__(self, users: UserRepository, loans: LoanRepository) -> None:
        """Bind the use case to the user and loan repository ports."""
        self._users = users
        self._loans = loans

    async def execute(self, query: LoanListQuery) -> LoanListResult:
        """List one page of the named user's loans, newest first."""
        user = await self._users.get_by_id(query.user_id)
        if user is None:
            raise UnknownUserError(query.user_id)
        # Two stable sorts: created_at descending, ties by loan id ascending
        # (the feature accepts either tie order; this one is deterministic).
        user_loans = await self._loans.list_by_user(query.user_id)
        ordered = sorted(user_loans, key=lambda loan: loan.loan_id)
        ordered.sort(key=lambda loan: loan.requested_on, reverse=True)
        start = (query.page - 1) * query.page_size
        return LoanListResult(
            items=ordered[start : start + query.page_size],
            total=len(ordered),
            page=query.page,
            page_size=query.page_size,
        )
