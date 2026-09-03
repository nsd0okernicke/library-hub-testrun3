"""SQLAlchemy ORM models for the loan service."""

from __future__ import annotations

from sqlalchemy import String
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
