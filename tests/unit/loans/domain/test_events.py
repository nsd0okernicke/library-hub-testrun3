"""Unit tests for the loan service domain events."""

from loans.domain.events import BookReturned
from loans.domain.isbn import Isbn


def test_book_returned_carries_loan_id_user_id_and_isbn() -> None:
    """The event names the loan, its user and its book, and nothing else."""
    isbn = Isbn("978-0-20-163361-0")
    event = BookReturned(loan_id="loan-1", user_id="user-1", isbn=isbn)

    assert event.loan_id == "loan-1"
    assert event.user_id == "user-1"
    assert event.isbn == isbn
    assert set(vars(event)) == {"loan_id", "user_id", "isbn"}


def test_book_returned_is_immutable() -> None:
    """A published event is a fact: its fields cannot be rewritten."""
    event = BookReturned(loan_id="loan-1", user_id="user-1", isbn=Isbn("978-0-20-163361-0"))

    try:
        event.loan_id = "other"  # type: ignore[misc]
    except AttributeError:
        pass
    else:  # pragma: no cover - frozen dataclasses always refuse
        raise AssertionError("BookReturned must be immutable")
