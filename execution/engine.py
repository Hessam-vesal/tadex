"""
Execution Engine - Order placement, tracking, and management.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import get_settings
from app.logger import get_logger

logger = get_logger("nobitex_trader.execution")


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    filled_price: float = 0
    commission: float = 0
    order_id: str = ""
    strategy_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"order_{uuid4().hex[:8]}"

    @property
    def is_complete(self) -> bool:
        return self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "strategy": self.strategy_name,
        }


class ExecutionEngine:
    """Execution engine for order management."""

    def __init__(self):
        """Initialize execution engine."""
        self._settings = get_settings()
        self._orders: Dict[str, Order] = {}
        self._active_orders: Dict[str, Order] = {}
        self._order_history: List[Order] = []
        self._stats = {"total": 0, "filled": 0, "failed": 0}
        logger.info("ExecutionEngine initialized")

    async def create_and_submit(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        strategy_name: str = "",
    ) -> Optional[Order]:
        """Create and submit an order."""
        if quantity <= 0:
            return None

        order = Order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            strategy_name=strategy_name,
        )

        self._orders[order.order_id] = order
        self._active_orders[order.order_id] = order
        self._stats["total"] += 1

        # Simulate order submission
        await asyncio.sleep(0.01)
        order.status = OrderStatus.FILLED
        order.filled_quantity = quantity
        order.filled_price = price or 0
        order.commission = quantity * 0.0015
        order.filled_at = datetime.now()

        self._stats["filled"] += 1
        if order.order_id in self._active_orders:
            del self._active_orders[order.order_id]
        self._order_history.append(order)

        logger.info(f"Order filled: {order.order_id} {side.value} {quantity} {symbol}")
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)

    def get_active_orders(self) -> List[Order]:
        """Get all active orders."""
        return list(self._active_orders.values())

    async def cancel_all_orders(self) -> int:
        """Cancel all active orders."""
        count = len(self._active_orders)
        for order in self._active_orders.values():
            order.status = OrderStatus.CANCELLED
            self._order_history.append(order)
        self._active_orders.clear()
        logger.info(f"Canceled {count} active orders")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {**self._stats, "active": len(self._active_orders)}
