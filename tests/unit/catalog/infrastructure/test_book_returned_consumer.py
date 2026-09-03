"""Unit tests for the BookReturned message-broker consumer adapter."""

from __future__ import annotations

from catalog.infrastructure.messaging.book_returned_consumer import BookReturnedConsumer


class _RecordingHandler:
    """Fake of the handle_book_returned use case that records the ISBNs seen."""

    def __init__(self) -> None:
        """Start with no recorded ISBNs."""
        self.isbns: list[str] = []

    async def handle(self, isbn: str) -> None:
        """Record the ISBN as handled."""
        self.isbns.append(isbn)


async def test_consumer_dispatches_isbn_from_broker_message() -> None:
    handler = _RecordingHandler()
    consumer = BookReturnedConsumer(handler)
    await consumer.on_message({"loan_id": "L1", "user_id": "U1", "isbn": "978-0-14-103614-3"})
    assert handler.isbns == ["978-0-14-103614-3"]


async def test_consumer_passes_missing_isbn_through_as_empty() -> None:
    handler = _RecordingHandler()
    consumer = BookReturnedConsumer(handler)
    await consumer.on_message({"loan_id": "L1", "user_id": "U1"})
    assert handler.isbns == [""]
