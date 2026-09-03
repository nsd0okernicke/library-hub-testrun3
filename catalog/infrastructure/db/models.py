"""SQLAlchemy ORM models for the catalog service."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for catalog ORM models."""


class BookRow(Base):
    """Row for the books table.

    The primary key is the ISBN as a 13-digit string, so ISBNs that differ
    only in hyphenation map to the same book.
    """

    __tablename__ = "books"

    isbn: Mapped[str] = mapped_column(String(13), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(200))
    genre: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    available_stock: Mapped[int] = mapped_column(Integer, default=0)
