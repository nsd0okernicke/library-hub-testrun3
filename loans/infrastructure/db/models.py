"""SQLAlchemy ORM models for the loan service."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for loan service ORM models."""


class UserRow(Base):
    """Row for the users table.

    The primary key is the system-generated user id; the email carries a
    unique constraint because it is the identity of an account.
    """

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)


class LoanRow(Base):
    """Row for the loans table.

    The primary key is the system-generated loan id. The due date is null
    until a PENDING loan is fulfilled.
    """

    __tablename__ = "loans"

    loan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    isbn: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16))
    requested_on: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
