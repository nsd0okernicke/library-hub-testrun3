"""Event publisher adapters for the loan service."""

from __future__ import annotations

from loans.domain.events import DomainEvent
from loans.domain.ports import DomainEventPublisher


class InMemoryEventPublisher(DomainEventPublisher):
    """Publisher that records events in memory, in publish order.

    Serves local runs and tests; a message-broker adapter (e.g. RabbitMQ)
    can replace it behind the same port.
    """

    def __init__(self) -> None:
        """Start with no published events."""
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        """Record the event in publish order."""
        self.events.append(event)
