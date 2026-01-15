"""Event system for ShopMind.

Provides an in-memory event bus for decoupled communication between
components. Can be swapped for Redis/Kafka in production.
"""

from shopmind.events.base import EventBus, Event, event_bus

__all__ = ["EventBus", "Event", "event_bus"]
