"""
Example Strategies - Sample trading strategy implementations.

Demonstrates how to create custom strategies using the indicator engine.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np

from app.config import get_settings
from app.logger import get_logger, strategy_logger
from strategy.base_strategy import (
    BaseStrategy,
    Signal,
    SignalStrength,
    StrategyConfig,
    TradingSignal,
)
from indicators.indicators import IndicatorEngine

logger = get_logger("nobitex_trader.examples")


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy - Trades based on price momentum.
    
    Uses EMA crossover, MACD, and RSI to identify momentum trades.
    
    Entry conditions (BUY):
    - EMA fast > EMA slow (uptrend)
    - MACD histogram > 0 (momentum positive)
    - RSI < 70 (not overbought)
    
    Entry conditions (SELL):
    - EMA fast < EMA slow (downtrend)
    - MACD histogram < 0 (momentum negative)
    - RSI > 30 (not oversold)
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize momentum strategy."""
        if config is None:
            config = StrategyConfig(
                name="momentum",
                params={
                    "ema_fast": 12,
                    "ema_slow": 26,
                    "rsi_period": 14,
                    "macd_signal": 9,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                },
            )
        super().__init__(config)
        
        params = self._config.params
        self._ema_fast_period = params.get("ema_fast", 12)
        self._ema_slow_period = params.get("ema_slow", 26)
        self._rsi_period = params.get("rsi_period", 14)
        self._macd_signal_period = params.get("macd_signal", 9)
        self._rsi_overbought = params.get("rsi_overbought", 70)
        self._rsi_oversold = params.get("rsi_oversold", 30)

    def initialize(self) -> bool:
        """Initialize the momentum strategy."""
        strategy_logger.info("MomentumStrategy initialized")
        return True

    def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data (not used directly in this strategy)."""
        pass

    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate momentum trading signal."""
        if not self._should_trade(symbol):
            return None

        # Get candles
        df = self.get_candles(symbol, limit=100)
        if len(df) < self._ema_slow_period + 10:
            return None

        try:
            # Calculate indicators
            engine = IndicatorEngine(df)
            ema_fast = engine.ema(df, self._ema_fast_period)
            ema_slow = engine.ema(df, self._ema_slow_period)
            rsi = engine.sma_rsi(df, self._rsi_period)
            macd_data = engine.macd(df, 12, 26, self._macd_signal_period)

            current_price = df["close"].iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_macd_hist = macd_data["histogram"].iloc[-1]
            prev_macd_hist = macd_data["histogram"].iloc[-2]
            current_ema_fast = ema_fast.iloc[-1]
            current_ema_slow = ema_slow.iloc[-1]

            # Skip if indicators are NaN
            if any(pd.isna([current_rsi, current_macd_hist, current_ema_fast, current_ema_slow])):
                return None

            # BUY signal
            if (current_ema_fast > current_ema_slow and
                current_macd_hist > 0 and
                current_rsi < self._rsi_overbought and
                prev_macd_hist <= 0):  # MACD crossover
                
                strength = SignalStrength.STRONG if current_rsi < 50 else SignalStrength.MODERATE
                stop_loss = current_price * 0.98  # 2% stop loss
                take_profit = current_price * 1.04  # 4% take profit
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.BUY,
                    strength=strength,
                    price=current_price,
                    reason=f"Momentum BUY: EMA fast {current_ema_fast:.0f} > slow {current_ema_slow:.0f}, MACD crossing up, RSI={current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "ema_fast": float(current_ema_fast),
                        "ema_slow": float(current_ema_slow),
                        "rsi": float(current_rsi),
                        "macd_hist": float(current_macd_hist),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

            # SELL signal
            elif (current_ema_fast < current_ema_slow and
                  current_macd_hist < 0 and
                  current_rsi > self._rsi_oversold and
                  prev_macd_hist >= 0):  # MACD crossover
                
                strength = SignalStrength.STRONG if current_rsi > 50 else SignalStrength.MODERATE
                stop_loss = current_price * 1.02  # 2% stop loss
                take_profit = current_price * 0.96  # 4% take profit
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.SELL,
                    strength=strength,
                    price=current_price,
                    reason=f"Momentum SELL: EMA fast {current_ema_fast:.0f} < slow {current_ema_slow:.0f}, MACD crossing down, RSI={current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "ema_fast": float(current_ema_fast),
                        "ema_slow": float(current_ema_slow),
                        "rsi": float(current_rsi),
                        "macd_hist": float(current_macd_hist),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

        except Exception as e:
            logger.error(f"Error in MomentumStrategy for {symbol}: {e}")

        return None


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy - Trades based on price returning to mean.
    
    Uses Bollinger Bands and RSI to identify overbought/oversold conditions.
    
    Entry conditions (BUY):
    - Price below lower Bollinger Band (oversold)
    - RSI < 30 (oversold)
    
    Entry conditions (SELL):
    - Price above upper Bollinger Band (overbought)
    - RSI > 70 (overbought)
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize mean reversion strategy."""
        if config is None:
            config = StrategyConfig(
                name="mean_reversion",
                params={
                    "bb_period": 20,
                    "bb_std": 2.0,
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                },
            )
        super().__init__(config)
        
        params = self._config.params
        self._bb_period = params.get("bb_period", 20)
        self._bb_std = params.get("bb_std", 2.0)
        self._rsi_period = params.get("rsi_period", 14)
        self._rsi_overbought = params.get("rsi_overbought", 70)
        self._rsi_oversold = params.get("rsi_oversold", 30)

    def initialize(self) -> bool:
        """Initialize the mean reversion strategy."""
        strategy_logger.info("MeanReversionStrategy initialized")
        return True

    def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data."""
        pass

    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate mean reversion trading signal."""
        if not self._should_trade(symbol):
            return None

        # Get candles
        df = self.get_candles(symbol, limit=100)
        if len(df) < self._bb_period + 10:
            return None

        try:
            # Calculate indicators
            engine = IndicatorEngine(df)
            bb = engine.bollinger_bands(df, self._bb_period, self._bb_std)
            rsi = engine.sma_rsi(df, self._rsi_period)

            current_price = df["close"].iloc[-1]
            current_rsi = rsi.iloc[-1]
            bb_lower = bb["lower"].iloc[-1]
            bb_upper = bb["upper"].iloc[-1]
            bb_middle = bb["middle"].iloc[-1]

            # Skip if NaN
            if any(pd.isna([current_rsi, bb_lower, bb_upper, bb_middle])):
                return None

            # BUY signal - price below lower band and oversold
            if (current_price < bb_lower and
                current_rsi < self._rsi_oversold):
                
                strength = SignalStrength.STRONG if current_rsi < 20 else SignalStrength.MODERATE
                stop_loss = bb_lower * 0.98  # Below lower band
                take_profit = bb_middle * 1.0  # Return to middle
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.BUY,
                    strength=strength,
                    price=current_price,
                    reason=f"Mean Reversion BUY: Price {current_price:.0f} < BB Lower {bb_lower:.0f}, RSI={current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "bb_lower": float(bb_lower),
                        "bb_middle": float(bb_middle),
                        "bb_upper": float(bb_upper),
                        "rsi": float(current_rsi),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

            # SELL signal - price above upper band and overbought
            elif (current_price > bb_upper and
                  current_rsi > self._rsi_overbought):
                
                strength = SignalStrength.STRONG if current_rsi > 80 else SignalStrength.MODERATE
                stop_loss = bb_upper * 1.02  # Above upper band
                take_profit = bb_middle * 1.0  # Return to middle
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.SELL,
                    strength=strength,
                    price=current_price,
                    reason=f"Mean Reversion SELL: Price {current_price:.0f} > BB Upper {bb_upper:.0f}, RSI={current_rsi:.1f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "bb_lower": float(bb_lower),
                        "bb_middle": float(bb_middle),
                        "bb_upper": float(bb_upper),
                        "rsi": float(current_rsi),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

        except Exception as e:
            logger.error(f"Error in MeanReversionStrategy for {symbol}: {e}")

        return None


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    Entry conditions (BUY):
    - SMA 20 crosses above SMA 50
    
    Entry conditions (SELL):
    - SMA 20 crosses below SMA 50
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize MA crossover strategy."""
        if config is None:
            config = StrategyConfig(
                name="ma_crossover",
                params={
                    "sma_fast": 20,
                    "sma_slow": 50,
                },
            )
        super().__init__(config)
        
        params = self._config.params
        self._sma_fast_period = params.get("sma_fast", 20)
        self._sma_slow_period = params.get("sma_slow", 50)

    def initialize(self) -> bool:
        """Initialize the strategy."""
        strategy_logger.info("MovingAverageCrossoverStrategy initialized")
        return True

    def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data."""
        pass

    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate MA crossover signal."""
        if not self._should_trade(symbol):
            return None

        df = self.get_candles(symbol, limit=100)
        if len(df) < self._sma_slow_period + 5:
            return None

        try:
            engine = IndicatorEngine(df)
            sma_fast = engine.sma(df, self._sma_fast_period)
            sma_slow = engine.sma(df, self._sma_slow_period)

            current_price = df["close"].iloc[-1]
            current_sma_fast = sma_fast.iloc[-1]
            current_sma_slow = sma_slow.iloc[-1]
            prev_sma_fast = sma_fast.iloc[-2]
            prev_sma_slow = sma_slow.iloc[-2]

            if any(pd.isna([current_sma_fast, current_sma_slow])):
                return None

            # BUY - fast crosses above slow
            if (prev_sma_fast <= prev_sma_slow and
                current_sma_fast > current_sma_slow):
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.BUY,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    reason=f"MA Crossover BUY: SMA{self._sma_fast_period} crossed above SMA{self._sma_slow_period}",
                    stop_loss=current_price * 0.98,
                    take_profit=current_price * 1.04,
                    metadata={
                        "sma_fast": float(current_sma_fast),
                        "sma_slow": float(current_sma_slow),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

            # SELL - fast crosses below slow
            elif (prev_sma_fast >= prev_sma_slow and
                  current_sma_fast < current_sma_slow):
                
                signal = self._create_signal(
                    symbol=symbol,
                    signal=Signal.SELL,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    reason=f"MA Crossover SELL: SMA{self._sma_fast_period} crossed below SMA{self._sma_slow_period}",
                    stop_loss=current_price * 1.02,
                    take_profit=current_price * 0.96,
                    metadata={
                        "sma_fast": float(current_sma_fast),
                        "sma_slow": float(current_sma_slow),
                    },
                )
                self.log_trade(signal, "signal")
                return signal

        except Exception as e:
            logger.error(f"Error in MovingAverageCrossoverStrategy for {symbol}: {e}")

        return None


# Register example strategies with factory
from strategy.strategy_manager import StrategyFactory
StrategyFactory.register("momentum", MomentumStrategy)
StrategyFactory.register("mean_reversion", MeanReversionStrategy)
StrategyFactory.register("ma_crossover", MovingAverageCrossoverStrategy)
