"""
Base Strategy - Abstract base class for trading strategies.

All strategies must inherit from BaseStrategy and implement
the required methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

from app.logger import get_logger

logger = get_logger("nobitex_trader.strategy")


class Signal(str, Enum):
    """Trading signals."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


class SignalStrength(str, Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class TradingSignal:
    """Represents a trading signal from a strategy."""
    symbol: str
    signal: Signal
    strength: SignalStrength
    strategy_name: str
    timestamp: datetime
    price: float
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "signal": self.signal.value,
            "strength": self.strength.value,
            "strategy": self.strategy_name,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "reason": self.reason,
            "metadata": self.metadata,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
        }


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy."""
    name: str
    enabled: bool = True
    symbols: List[str] = field(default_factory=lambda: [])
    timeframe: str = "15m"
    params: Dict[str, Any] = field(default_factory=dict)
    risk_percent: Optional[float] = None  # Override global risk per trade


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Every strategy must implement:
    - initialize(): Set up initial state and parameters
    - on_market_data(): Process new market data
    - generate_signal(): Generate trading signals
    
    Optional methods:
    - on_tick(): Called on every tick
    - on_candle(): Called when a new candle forms
    - on_order_filled(): Called when an order is filled
    - on_position_updated(): Called when position changes
    - cleanup(): Clean up resources
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize base strategy."""
        self._config = config or StrategyConfig(name=self.__class__.__name__)
        self._position: Optional[Dict[str, Any]] = None
        self._trade_log: List[Dict[str, Any]] = []
        self._is_initialized = False
        self._last_signal: Optional[TradingSignal] = None
        self._signal_count = 0
        self._data_cache: Dict[str, pd.DataFrame] = {}
        
        logger.info(f"Strategy initialized: {self._config.name}")

    @property
    def name(self) -> str:
        """Get strategy name."""
        return self._config.name

    @property
    def config(self) -> StrategyConfig:
        """Get strategy config."""
        return self._config

    @property
    def position(self) -> Optional[Dict[str, Any]]:
        """Get current position."""
        return self._position

    @property
    def trade_log(self) -> List[Dict[str, Any]]:
        """Get trade log."""
        return self._trade_log

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the strategy.
        
        Called once when strategy starts.
        Set up indicators, load data, initialize state.
        
        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """
        Process new market data.
        
        Args:
            symbol: Trading pair symbol
            data: Market data dictionary (ticker, order book, etc.)
        """
        pass

    @abstractmethod
    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """
        Generate trading signal.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            TradingSignal if signal generated, None otherwise
        """
        pass

    def on_tick(self, symbol: str, ticker: Dict[str, Any]):
        """Called on every tick update (optional)."""
        pass

    def on_candle(self, symbol: str, candle: Dict[str, Any]):
        """Called when a new candle forms (optional)."""
        pass

    def on_order_filled(self, symbol: str, order: Dict[str, Any]):
        """Called when an order is filled (optional)."""
        self._trade_log.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "type": "fill",
            "data": order,
        })

    def on_position_updated(self, symbol: str, position: Dict[str, Any]):
        """Called when position changes (optional)."""
        self._position = position

    def cleanup(self):
        """Clean up resources (optional)."""
        self._data_cache.clear()
        logger.info(f"Strategy cleanup: {self._config.name}")

    def get_candles(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Get cached candles for a symbol."""
        return self._data_cache.get(symbol, pd.DataFrame())

    def cache_candles(self, symbol: str, candles: pd.DataFrame):
        """Cache candles for a symbol."""
        self._data_cache[symbol] = candles

    def log_trade(self, signal: TradingSignal, action: str):
        """Log a trading action."""
        self._trade_log.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": signal.symbol,
            "type": action,
            "signal": signal.to_dict(),
        })

    def _create_signal(
        self,
        symbol: str,
        signal: Signal,
        strength: SignalStrength,
        price: float,
        reason: str = "",
        **kwargs,
    ) -> TradingSignal:
        """Create a trading signal."""
        self._signal_count += 1
        self._last_signal = TradingSignal(
            symbol=symbol,
            signal=signal,
            strength=strength,
            strategy_name=self._config.name,
            timestamp=datetime.now(),
            price=price,
            reason=reason,
            target_price=kwargs.get("target_price"),
            stop_loss=kwargs.get("stop_loss"),
            take_profit=kwargs.get("take_profit"),
            metadata=kwargs.get("metadata", {}),
        )
        return self._last_signal

    def _should_trade(self, symbol: str) -> bool:
        """Check if trading is allowed for a symbol."""
        if not self._config.enabled:
            return False

        if not self._is_initialized:
            return False

        # Check symbol filter
        if self._config.symbols and symbol not in self._config.symbols:
            return False

        return True
