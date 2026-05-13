"""
Event Engine - Core event-driven architecture for the trading system.

Implements a publish/subscribe pattern for decoupled communication
between system components.
"""

import asyncio
import heapq
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.logger import get_logger

logger = get_logger("nobitex_trader.event_engine")


class EventType(str, Enum):
    """Types of events in the trading system."""
    # Market Data Events
    TICKER_UPDATE = "ticker_update"
    ORDER_BOOK_UPDATE = "order_book_update"
    TRADE_EXECUTED = "trade_executed"
    CANDLE_UPDATE = "candle_update"

    # Trading Events
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_FILLED = "order_filled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"

    # Risk Events
    RISK_CHECK = "risk_check"
    DRAWDOWN_ALERT = "drawdown_alert"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"

    # Portfolio Events
    PORTFOLIO_UPDATE = "portfolio_update"
    PNL_UPDATE = "pnl_update"

    # System Events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"
    WARNING = "warning"

    # Notification Events
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"


@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""

    def __lt__(self, other: "Event") -> bool:
        """Compare events for priority queue."""
        return self.timestamp < other.timestamp

    def __repr__(self) -> str:
        return f"Event({self.event_type.value}, id={self.event_id[:8]}, source={self.source})"


class EventHandler:
    """Base class for event handlers."""

    def __init__(self, event_type: EventType):
        """Initialize event handler."""
        self.event_type = event_type
        self.enabled = True

    def handle(self, event: Event) -> Optional[Any]:
        """Handle an event. Override in subclass."""
        raise NotImplementedError


class EventEngine:
    """
    Core event engine that routes events to registered handlers.
    
    Supports:
    - Synchronous event handling
    - Asynchronous event handling
    - Priority-based event processing
    - One-time and recurring subscriptions
    - Event filtering
    """

    def __init__(self, async_mode: bool = True):
        """Initialize event engine."""
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._running = False
        self._event_queue: List[tuple] = []
        self._event_counter = 0
        self._async_mode = async_mode
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Event history for debugging
        self._event_history: List[Event] = []
        self._max_history = 1000

        logger.info(f"EventEngine initialized (async_mode={async_mode})")

    def start(self):
        """Start the event engine."""
        self._running = True
        if self._async_mode:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        logger.info("EventEngine started")

    def stop(self):
        """Stop the event engine."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.stop()
        logger.info("EventEngine stopped")

    def register(
        self,
        event_type: EventType,
        handler: Callable,
        once: bool = False,
    ):
        """
        Register a synchronous event handler.

        Args:
            event_type: Type of event to handle
            handler: Handler function
            once: If True, handler is removed after first execution
        """
        self._handlers[event_type].append({
            "func": handler,
            "once": once,
            "id": str(uuid.uuid4()),
        })
        logger.debug(f"Registered sync handler for {event_type.value}")

    def register_async(
        self,
        event_type: EventType,
        handler: Callable,
        once: bool = False,
    ):
        """
        Register an asynchronous event handler.

        Args:
            event_type: Type of event to handle
            handler: Async handler function
            once: If True, handler is removed after first execution
        """
        self._async_handlers[event_type].append({
            "func": handler,
            "once": once,
            "id": str(uuid.uuid4()),
        })
        logger.debug(f"Registered async handler for {event_type.value}")

    def unregister(self, event_type: EventType, handler_id: str):
        """Unregister a handler by ID."""
        for handlers in [self._handlers, self._async_handlers]:
            for h in handlers.get(event_type, []):
                if h["id"] == handler_id:
                    handlers[event_type].remove(h)
                    logger.debug(f"Unregistered handler {handler_id} for {event_type.value}")
                    return

    def emit(self, event: Event, wait: bool = False) -> Optional[Any]:
        """
        Emit an event to all registered handlers.

        Args:
            event: The event to emit
            wait: If True, wait for all async handlers to complete

        Returns:
            List of handler return values (for sync handlers)
        """
        if not self._running:
            logger.warning(f"EventEngine not running, event dropped: {event}")
            return None

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        logger.debug(f"Emitting event: {event}")
        results = []

        # Process sync handlers
        sync_handlers = self._handlers.get(event.event_type, [])
        for h_info in sync_handlers:
            try:
                result = h_info["func"](event)
                if result is not None:
                    results.append(result)
                if h_info["once"]:
                    self.unregister(event.event_type, h_info["id"])
            except Exception as e:
                logger.error(f"Sync handler error for {event.event_type}: {e}")

        # Process async handlers
        async_handlers = self._async_handlers.get(event.event_type, [])
        if async_handlers:
            if self._loop and self._loop.is_running():
                tasks = [
                    self._execute_async_handler(h_info["func"], event)
                    for h_info in async_handlers
                ]
                if wait:
                    async_results = self._loop.run_until_complete(
                        asyncio.gather(*tasks, return_exceptions=True)
                    )
                    results.extend(async_results)
            else:
                # Queue for later processing
                for h_info in async_handlers:
                    self._event_queue.append((event.timestamp, self._event_counter, h_info))
                    self._event_counter += 1

        return results if results else None

    def emit_batch(self, events: List[Event]):
        """Emit multiple events in batch."""
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        for event in events:
            self.emit(event)

    async def _execute_async_handler(self, handler: Callable, event: Event):
        """Execute an async handler."""
        try:
            result = await handler(event)
            return result
        except Exception as e:
            logger.error(f"Async handler error for {event.event_type}: {e}")
            return None

    def process_queue(self):
        """Process queued events in priority order."""
        processed = 0
        while self._event_queue:
            _, _, h_info = heapq.heappop(self._event_queue)
            try:
                h_info["func"]  # Sync handler - execute directly
                processed += 1
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
        return processed

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get recent event history."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_event_count(self, event_type: Optional[EventType] = None) -> int:
        """Get count of events."""
        if event_type:
            return sum(1 for e in self._event_history if e.event_type == event_type)
        return len(self._event_history)

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        logger.debug("Event history cleared")


class EventBus:
    """
    Higher-level event bus with topic-based subscriptions.
    
    Provides a more user-friendly interface for publishing and subscribing
    to events.
    """

    def __init__(self):
        """Initialize event bus."""
        self._engine = EventEngine(async_mode=True)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to a topic."""
        self._subscribers[topic].append(callback)
        event_type = self._topic_to_event(topic)
        self._engine.register(event_type, callback)

    def subscribe_async(self, topic: str, callback: Callable):
        """Subscribe to a topic with async handler."""
        self._subscribers[topic].append(callback)
        event_type = self._topic_to_event(topic)
        self._engine.register_async(event_type, callback)

    def publish(self, topic: str, data: Optional[Dict] = None) -> Event:
        """Publish an event to a topic."""
        event = Event(
            event_type=self._topic_to_event(topic),
            data=data or {},
            source="event_bus",
        )
        self._engine.emit(event)
        return event

    def start(self):
        """Start the event bus."""
        self._engine.start()

    def stop(self):
        """Stop the event bus."""
        self._engine.stop()

    @staticmethod
    def _topic_to_event(topic: str) -> EventType:
        """Convert topic string to EventType."""
        try:
            return EventType(topic)
        except ValueError:
            # Default to error event for unknown topics
            return EventType.ERROR

    @property
    def engine(self) -> EventEngine:
        """Get the underlying event engine."""
        return self._engine
