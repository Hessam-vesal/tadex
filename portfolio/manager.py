"""
Portfolio Manager - Portfolio optimization and position management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.logger import get_logger

logger = get_logger("nobitex_trader.portfolio")


@dataclass
class AssetBalance:
    """Balance for a single asset."""
    asset: str
    free: float = 0
    locked: float = 0

    @property
    def total(self) -> float:
        return self.free + self.locked


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state."""
    timestamp: datetime
    total_value: float
    assets: Dict[str, float]
    cash_balance: float
    cash_percent: float
    returns: float = 0


class PortfolioManager:
    """Manages portfolio state and allocations."""

    def __init__(self):
        """Initialize portfolio manager."""
        self._balances: Dict[str, AssetBalance] = {}
        self._snapshots: List[PortfolioSnapshot] = []
        self._initial_capital: float = 0
        self._peak_value: float = 0
        logger.info("PortfolioManager initialized")

    def update_balance(self, asset: str, free: float, locked: float = 0):
        """Update balance for an asset."""
        if asset in self._balances:
            self._balances[asset].free = free
            self._balances[asset].locked = locked
        else:
            self._balances[asset] = AssetBalance(asset=asset, free=free, locked=locked)

    def get_balance(self, asset: str) -> float:
        """Get free balance for an asset."""
        return self._balances.get(asset, AssetBalance(asset=asset)).free

    def get_total_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value."""
        total = 0
        for asset, balance in self._balances.items():
            price = prices.get(asset, 0)
            total += balance.total * price
        return total

    def get_allocation(self, prices: Dict[str, float]) -> Dict[str, float]:
        """Get portfolio allocation percentages."""
        total = self.get_total_value(prices)
        if total == 0:
            return {}
        allocation = {}
        for asset, balance in self._balances.items():
            allocation[asset] = (balance.total * prices.get(asset, 0)) / total
        return allocation

    def take_snapshot(self, prices: Optional[Dict[str, float]] = None):
        """Take a portfolio snapshot."""
        if prices is None:
            prices = {}
        total = self.get_total_value(prices)
        if total > self._peak_value:
            self._peak_value = total

        cash = self.get_balance("IRT")
        cash_pct = (cash / total * 100) if total > 0 else 100

        assets = {}
        for asset, balance in self._balances.items():
            if asset != "IRT" and balance.total > 0:
                assets[asset] = balance.total

        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=total,
            assets=assets,
            cash_balance=cash,
            cash_percent=cash_pct,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_snapshot(self, index: int = -1) -> Optional[PortfolioSnapshot]:
        """Get a portfolio snapshot."""
        if not self._snapshots:
            return None
        return self._snapshots[index]

    def get_performance(self) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        if not self._snapshots:
            return {"total_return": 0, "sharpe_ratio": 0, "max_drawdown": 0}

        first = self._snapshots[0]
        last = self._snapshots[-1]
        total_return = ((last.total_value - first.total_value) / first.total_value * 100) if first.total_value > 0 else 0
        max_drawdown = 0
        peak = first.total_value
        for s in self._snapshots:
            if s.total_value > peak:
                peak = s.total_value
            dd = (peak - s.total_value) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, dd)

        returns = [
            (s.total_value - self._snapshots[i-1].total_value) / self._snapshots[i-1].total_value
            for i, s in enumerate(self._snapshots[1:], 1)
            if self._snapshots[i-1].total_value > 0
        ]
        sharpe = (sum(returns) / len(returns) * 252 / (sum(r**2 for r in returns) / len(returns) ** 0.5 if returns else 1)) if returns else 0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "current_value": last.total_value,
            "initial_value": first.total_value,
            "num_snapshots": len(self._snapshots),
        }

    def get_all_balances(self) -> Dict[str, AssetBalance]:
        return dict(self._balances)
