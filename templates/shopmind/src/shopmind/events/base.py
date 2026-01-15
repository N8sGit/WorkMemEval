"""
Event bus implementation for decoupled communication.

This is a simple in-memory event bus for local development.
In production, this can be swapped for Redis pub/sub, Kafka, etc.

Design goals:
- Minimal coupling between event producers and consumers
- Easy to extend with new event types
- Foundation for future ML/analytics pipelines
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from collections import defaultdict
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Event(ABC):
    """
    Base class for all domain events.

    Subclasses should be dataclasses with specific event data.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1  # For event schema versioning

    @property
    def event_type(self) -> str:
        """Get the event type name (class name by default)."""
        return self.__class__.__name__


# --- Domain Events ---
# These represent significant occurrences in the system

@dataclass
class UserRegistered(Event):
    """Emitted when a new user registers."""
    user_id: int = 0
    email: str = ""


@dataclass
class UserLoggedIn(Event):
    """Emitted when a user logs in."""
    user_id: int = 0


@dataclass
class ProductViewed(Event):
    """Emitted when a user views a product."""
    product_id: int = 0
    user_id: int | None = None  # None for anonymous views


@dataclass
class ProductCreated(Event):
    """Emitted when a new product is created."""
    product_id: int = 0


@dataclass
class StockUpdated(Event):
    """Emitted when product stock changes."""
    variant_id: int = 0
    old_quantity: int = 0
    new_quantity: int = 0


@dataclass
class LowStockWarning(Event):
    """Emitted when stock falls below threshold."""
    variant_id: int = 0
    sku: str = ""
    current_quantity: int = 0
    threshold: int = 0


# Handler type: function that takes an event and returns nothing
EventHandler = Callable[[Event], None]


class EventBus:
    """
    Simple in-memory event bus.

    Supports:
    - Subscribing handlers to specific event types
    - Wildcard handlers that receive all events
    - Sync event emission (handlers run immediately)

    TODO: Add async support
    TODO: Add dead letter queue for failed handlers
    TODO: Add event persistence for replay
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The Event subclass to subscribe to
            handler: Function to call when event is emitted
        """
        self._handlers[event_type.__name__].append(handler)
        logger.debug(f"Subscribed handler to {event_type.__name__}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to ALL events (wildcard).

        Useful for logging, analytics, etc.
        """
        self._global_handlers.append(handler)
        logger.debug("Subscribed global handler")

    def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribed handlers.

        Handlers are called synchronously in subscription order.
        Exceptions in handlers are logged but don't stop other handlers.
        """
        event_type = event.event_type
        logger.info(f"Event emitted: {event_type} (id={event.event_id})")

        # Call type-specific handlers
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global handler error for {event_type}: {e}")

    def clear(self) -> None:
        """Remove all handlers. Useful for testing."""
        self._handlers.clear()
        self._global_handlers.clear()


# Global event bus instance
# In production, this might be configured differently (e.g., connected to Redis)
event_bus = EventBus()


# --- Default Handlers ---

def log_event_handler(event: Event) -> None:
    """Simple handler that logs all events. Useful for debugging."""
    logger.info(
        f"[EVENT] {event.event_type} at {event.timestamp.isoformat()} | "
        f"id={event.event_id}"
    )


# Register the logging handler by default in debug mode
# TODO: Make this configurable
# event_bus.subscribe_all(log_event_handler)
