"""
Strategy Manager - Manages multiple trading strategies.

Handles strategy registration, execution, and signal aggregation.
"""

from typing import Dict, List, Optional, Type
from datetime import datetime

import pandas as pd

from app.config import get_settings
from app.logger import get_logger, strategy_logger
from strategy.base_strategy import (
    BaseStrategy,
    Signal,
    SignalStrength,
    StrategyConfig,
    TradingSignal,
)

logger = get_logger("nobitex_trader.strategy_manager")


class SignalAggregator:
    """Aggregates signals from multiple strategies."""

    def __init__(self):
        """Initialize signal aggregator."""
        self._signal_weights = {
            SignalStrength.STRONG: 2.0,
            SignalStrength.MODERATE: 1.0,
            SignalStrength.WEAK: 0.5,
        }

    def aggregate(
        self, signals: List[TradingSignal]
    ) -> Optional[TradingSignal]:
        """
        Aggregate multiple signals into one decision.
        
        Uses weighted scoring to determine overall signal.
        """
        if not signals:
            return None

        buy_score = 0
        sell_score = 0

        for signal in signals:
            weight = self._signal_weights.get(signal.strength, 1.0)
            if signal.signal in (Signal.BUY, Signal.CLOSE_SHORT):
                buy_score += weight
            elif signal.signal in (Signal.SELL, Signal.CLOSE_LONG):
                sell_score += weight

        if buy_score > sell_score * 1.5:
            strongest = max(signals, key=lambda s: s.strength.value)
            if strongest.signal == Signal.BUY:
                return strongest
            # Create aggregated buy signal
            return TradingSignal(
                symbol=signals[0].symbol,
                signal=Signal.BUY,
                strength=SignalStrength.STRONG if buy_score > 3 else SignalStrength.MODERATE,
                strategy_name="aggregated",
                timestamp=datetime.now(),
                price=strongest.price,
                reason=f"Buy score: {buy_score:.1f} vs Sell: {sell_score:.1f}",
            )
        elif sell_score > buy_score * 1.5:
            strongest = max(signals, key=lambda s: s.strength.value)
            if strongest.signal == Signal.SELL:
                return strongest
            return TradingSignal(
                symbol=signals[0].symbol,
                signal=Signal.SELL,
                strength=SignalStrength.STRONG if sell_score > 3 else SignalStrength.MODERATE,
                strategy_name="aggregated",
                timestamp=datetime.now(),
                price=strongest.price,
                reason=f"Sell score: {sell_score:.1f} vs Buy: {buy_score:.1f}",
            )

        return None


class StrategyManager:
    """
    Manages the lifecycle of trading strategies.
    
    Responsibilities:
    - Register and unregister strategies
    - Initialize all strategies
    - Feed market data to strategies
    - Collect and aggregate signals
    - Track strategy performance
    """

    def __init__(self):
        """Initialize strategy manager."""
        self._strategies: Dict[str, BaseStrategy] = {}
        self._signal_aggregator = SignalAggregator()
        self._settings = get_settings()
        self._is_running = False

        logger.info("StrategyManager initialized")

    def register_strategy(self, strategy: BaseStrategy) -> bool:
        """
        Register a strategy.
        
        Args:
            strategy: Strategy instance to register
            
        Returns:
            True if registration successful
        """
        name = strategy.name
        if name in self._strategies:
            logger.warning(f"Strategy '{name}' already registered, replacing")

        self._strategies[name] = strategy
        logger.info(f"Strategy registered: {name}")
        return True

    def unregister_strategy(self, name: str) -> bool:
        """Unregister a strategy."""
        if name not in self._strategies:
            return False

        strategy = self._strategies[name]
        strategy.cleanup()
        del self._strategies[name]
        logger.info(f"Strategy unregistered: {name}")
        return True

    def initialize_all(self) -> bool:
        """Initialize all registered strategies."""
        all_success = True

        for name, strategy in self._strategies.items():
            try:
                success = strategy.initialize()
                strategy._is_initialized = success
                if not success:
                    all_success = False
                    logger.error(f"Failed to initialize strategy: {name}")
                else:
                    logger.info(f"Strategy initialized successfully: {name}")
            except Exception as e:
                all_success = False
                logger.error(f"Error initializing {name}: {e}")

        self._is_running = all_success
        return all_success

    def process_market_data(self, symbol: str, data: Dict):
        """
        Feed market data to all strategies.
        
        Args:
            symbol: Trading pair symbol
            data: Market data
        """
        for name, strategy in self._strategies.items():
            try:
                if symbol in strategy.config.symbols or not strategy.config.symbols:
                    strategy.on_market_data(symbol, data)
            except Exception as e:
                logger.error(f"Error in strategy {name}: {e}")

    def generate_signals(self, symbol: str) -> List[TradingSignal]:
        """
        Generate signals from all strategies for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of trading signals
        """
        signals = []

        for name, strategy in self._strategies.items():
            try:
                if symbol in strategy.config.symbols or not strategy.config.symbols:
                    signal = strategy.generate_signal(symbol)
                    if signal:
                        signals.append(signal)
                        strategy_logger.info(
                            f"Signal from {name}: {signal.signal.value} "
                            f"{signal.symbol} @ {signal.price} "
                            f"({signal.strength.value}): {signal.reason}"
                        )
            except Exception as e:
                logger.error(f"Error generating signals from {name}: {e}")

        return signals

    def get_aggregated_signal(self, symbol: str) -> Optional[TradingSignal]:
        """
        Get aggregated signal for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Aggregated trading signal or None
        """
        signals = self.generate_signals(symbol)
        return self._signal_aggregator.aggregate(signals)

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name."""
        return self._strategies.get(name)

    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """Get all registered strategies."""
        return dict(self._strategies)

    def get_strategy_status(self) -> Dict[str, Dict]:
        """Get status of all strategies."""
        status = {}
        for name, strategy in self._strategies.items():
            status[name] = {
                "enabled": strategy.config.enabled,
                "initialized": strategy._is_initialized,
                "signal_count": strategy._signal_count,
                "last_signal": strategy._last_signal.to_dict() if strategy._last_signal else None,
                "trade_log_count": len(strategy.trade_log),
            }
        return status

    def get_all_signals_history(self) -> List[TradingSignal]:
        """Get all signals from all strategies."""
        all_signals = []
        for strategy in self._strategies.values():
            for trade in strategy.trade_log:
                if trade.get("type") == "signal":
                    all_signals.append(trade.get("signal"))
        return all_signals

    @property
    def is_running(self) -> bool:
        """Check if strategy manager is running."""
        return self._is_running

    def stop(self):
        """Stop all strategies."""
        for name, strategy in self._strategies.items():
            strategy.cleanup()
        self._is_running = False
        logger.info("StrategyManager stopped")


# Strategy factory for easy creation
class StrategyFactory:
    """Factory for creating strategy instances."""

    _strategy_registry: Dict[str, Type[BaseStrategy]] = {}

    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy]):
        """Register a strategy class."""
        cls._strategy_registry[name] = strategy_class

    @classmethod
    def create(cls, name: str, config: Optional[StrategyConfig] = None) -> BaseStrategy:
        """Create a strategy by name."""
        if name not in cls._strategy_registry:
            raise ValueError(f"Unknown strategy: {name}")

        return cls._strategy_registry[name](config)

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy names."""
        return list(cls._strategy_registry.keys())
