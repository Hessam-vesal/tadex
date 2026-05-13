"""
Database module - Trade and configuration persistence.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class TradeRepository:
    """Stores and retrieves trade data."""

    def __init__(self, db_path: str = "data/trades.db"):
        self._trades: List[Dict] = []
        self._signals: List[Dict] = []

    def save_trade(self, trade: Dict[str, Any]) -> bool:
        trade["id"] = len(self._trades) + 1
        trade["created_at"] = datetime.now().isoformat()
        self._trades.append(trade)
        return True

    def get_trades(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        trades = self._trades
        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]
        return trades[-limit:]

    def save_signal(self, signal: Dict[str, Any]) -> bool:
        signal["id"] = len(self._signals) + 1
        signal["created_at"] = datetime.now().isoformat()
        self._signals.append(signal)
        return True

    def get_signals(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        signals = self._signals
        if symbol:
            signals = [s for s in signals if s.get("symbol") == symbol]
        return signals[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_trades": len(self._trades),
            "total_signals": len(self._signals),
        }
