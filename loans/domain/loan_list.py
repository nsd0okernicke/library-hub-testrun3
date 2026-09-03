"""Loan list query and result value objects for the loan service."""

from __future__ import annotations

from dataclasses import dataclass, field

from loans.domain.exceptions import InvalidLoanListParametersError
from loans.domain.loan import Loan

#: First page of a paginated loan list (same scheme as the catalog search).
DEFAULT_PAGE = 1
#: Page size applied when the caller does not name one.
DEFAULT_PAGE_SIZE = 20
#: Largest page size the loan list accepts.
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class LoanListQuery:
    """Immutable request for one page of a single user's loans.

    ``page`` is 1-indexed and ``page_size`` must lie in
    ``1..MAX_PAGE_SIZE``; the user id must name an account.
    """

    user_id: str
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        """Reject pagination values outside the valid range."""
        if not self.user_id:
            raise InvalidLoanListParametersError("user id must not be empty")
        if self.page < DEFAULT_PAGE:
            raise InvalidLoanListParametersError("page must be >= 1")
        if self.page_size < DEFAULT_PAGE:
            raise InvalidLoanListParametersError("page size must be >= 1")
        if self.page_size > MAX_PAGE_SIZE:
            raise InvalidLoanListParametersError(f"page size must be <= {MAX_PAGE_SIZE}")


@dataclass(slots=True)
class LoanListResult:
    """One page of a user's loans.

    ``items`` holds the loans on this page only, newest first; ``total``
    counts every loan of the user, not only this page.
    """

    items: list[Loan] = field(default_factory=list)
    total: int = 0
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE
