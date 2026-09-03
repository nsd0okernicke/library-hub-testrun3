"""Consumer adapter for BookReturned broker messages.

Delivers the ISBN carried by each BookReturned message to the
handle-book-returned use case. A message-broker transport (e.g. RabbitMQ)
binds its delivery callback to ``on_message``; the adapter itself stays
transport-agnostic and testable without a broker.
"""

from __future__ import annotations

from typing import Any, Protocol


class BookReturnedHandler(Protocol):
    """Use case that applies one BookReturned event."""

    async def handle(self, isbn: str) -> None:
        """Increase the stock of the named book, ignoring unknown ISBNs."""


class BookReturnedConsumer:
    """Forwards the ISBN of each consumed BookReturned message to the use case."""

    def __init__(self, handler: BookReturnedHandler) -> None:
        """Bind the consumer to the handle-book-returned use case."""
        self._handler = handler

    async def on_message(self, message: dict[str, Any]) -> None:
        """Decode one broker message and dispatch its ISBN to the use case.

        A missing ISBN is passed through as an empty string, which the
        use case ignores like any other invalid ISBN.
        """
        await self._handler.handle(str(message.get("isbn", "")))
