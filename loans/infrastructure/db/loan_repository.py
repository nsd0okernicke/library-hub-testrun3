"""SQLAlchemy implementation of the LoanRepository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from loans.domain.isbn import Isbn
from loans.domain.loan import Loan, LoanStatus
from loans.domain.ports import LoanRepository
from loans.infrastructure.db.models import LoanRow


def _to_domain(row: LoanRow) -> Loan:
    """Map an ORM row to the Loan domain entity."""
    return Loan(
        loan_id=row.loan_id,
        user_id=row.user_id,
        isbn=Isbn(row.isbn),
        requested_on=row.requested_on,
        status=LoanStatus(row.status),
        due_date=row.due_date,
    )


def _to_row(loan: Loan) -> LoanRow:
    """Map a Loan domain entity to an ORM row."""
    return LoanRow(
        loan_id=loan.loan_id,
        user_id=loan.user_id,
        isbn=loan.isbn.value,
        status=loan.status.value,
        requested_on=loan.requested_on,
        due_date=loan.due_date,
    )


class SqlAlchemyLoanRepository(LoanRepository):
    """Persists loan records in PostgreSQL through SQLAlchemy (asyncpg driver)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind the repository to a session factory."""
        self._sessions = sessions

    async def get(self, loan_id: str) -> Loan | None:
        """Return the loan for the loan id, or None when not present."""
        async with self._sessions() as session:
            result = await session.execute(select(LoanRow).where(LoanRow.loan_id == loan_id))
            row = result.scalar_one_or_none()
            return _to_domain(row) if row is not None else None

    async def save(self, loan: Loan) -> None:
        """Insert or update a loan record."""
        row = _to_row(loan)
        async with self._sessions() as session:
            await session.merge(row)
            await session.commit()

    async def count(self) -> int:
        """Return the total number of loans."""
        async with self._sessions() as session:
            result = await session.scalar(select(func.count()).select_from(LoanRow))
            return int(result or 0)
