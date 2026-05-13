"""
Indicator Engine - Technical analysis indicator calculations.

Provides a comprehensive set of technical indicators used by trading
strategies. All indicators work with pandas DataFrames for performance.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

from app.logger import get_logger

logger = get_logger("nobitex_trader.indicators")


class IndicatorType(str, Enum):
    """Types of indicators."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    REGRESSION = "regression"


class IndicatorEngine:
    """
    Engine for calculating technical indicators.
    
    Allows strategies to dynamically request indicators with
    configurable parameters.
    
    Example usage:
        engine = IndicatorEngine(df)
        ema_fast = engine.ema(df['close'], period=20)
        ema_slow = engine.ema(df['close'], period=50)
        rsi = engine.sma_rsi(df['close'], period=14)
    """

    # Registry of indicator names to calculation functions
    _indicators: Dict[str, Tuple[IndicatorType, callable]] = {}

    def __init__(self, data: pd.DataFrame):
        """
        Initialize indicator engine.
        
        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        """
        self._data = data.copy()
        self._cache: Dict[str, pd.Series] = {}
        logger.debug(f"IndicatorEngine initialized with {len(data)} rows")

    @property
    def data(self) -> pd.DataFrame:
        """Get the input data."""
        return self._data

    def calculate(self, name: str, params: Optional[Dict] = None) -> pd.Series:
        """
        Calculate an indicator by name.
        
        Args:
            name: Indicator name (e.g., 'ema', 'sma', 'rsi')
            params: Indicator parameters
            
        Returns:
            Series with indicator values
        """
        params = params or {}
        cache_key = f"{name}_{params}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        if name not in self._indicators:
            raise ValueError(f"Unknown indicator: {name}")

        indicator_type, func = self._indicators[name]
        result = func(self._data, **params)

        if isinstance(result, pd.Series):
            self._cache[cache_key] = result
        return result

    def get_indicator_info(self, name: str) -> Optional[Dict]:
        """Get information about an indicator."""
        if name not in self._indicators:
            return None
        indicator_type, _ = self._indicators[name]
        return {"name": name, "type": indicator_type.value}

    # ========== TREND INDICATORS ==========

    @classmethod
    def _register(cls):
        """Register all indicators."""
        # Simple Moving Average
        cls._indicators["sma"] = (IndicatorType.TREND, lambda data, **kwargs: cls.sma(data, **kwargs))
        # Exponential Moving Average
        cls._indicators["ema"] = (IndicatorType.TREND, lambda data, **kwargs: cls.ema(data, **kwargs))
        # Weighted Moving Average
        cls._indicators["wma"] = (IndicatorType.TREND, lambda data, **kwargs: cls.wma(data, **kwargs))
        # Smoothed Moving Average
        cls._indicators["smma"] = (IndicatorType.TREND, lambda data, **kwargs: cls.smma(data, **kwargs))
        # Double Exponential Moving Average
        cls._indicators["dema"] = (IndicatorType.TREND, lambda data, **kwargs: cls.dema(data, **kwargs))
        # Triple Exponential Moving Average
        cls._indicators["tema"] = (IndicatorType.TREND, lambda data, **kwargs: cls.tema(data, **kwargs))
        # RSI
        cls._indicators["rsi"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.sma_rsi(data, **kwargs))
        cls._indicators["sma_rsi"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.sma_rsi(data, **kwargs))
        # CCI
        cls._indicators["cci"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.cci(data, **kwargs))
        # ADX
        cls._indicators["adx"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.adx(data, **kwargs))
        # MACD
        cls._indicators["macd"] = (IndicatorType.TREND, lambda data, **kwargs: cls.macd(data, **kwargs))
        # Bollinger Bands
        cls._indicators["bollinger"] = (IndicatorType.VOLATILITY, lambda data, **kwargs: cls.bollinger_bands(data, **kwargs))
        # ATR
        cls._indicators["atr"] = (IndicatorType.VOLATILITY, lambda data, **kwargs: cls.atr(data, **kwargs))
        # MFI
        cls._indicators["mfi"] = (IndicatorType.VOLUME, lambda data, **kwargs: cls.mfi(data, **kwargs))
        # VWAP
        cls._indicators["vwap"] = (IndicatorType.TREND, lambda data, **kwargs: cls.vwap(data, **kwargs))
        # Ichimoku
        cls._indicators["ichimoku"] = (IndicatorType.TREND, lambda data, **kwargs: cls.ichimoku(data, **kwargs))
        # Parabolic SAR
        cls._indicators["parabolic_sar"] = (IndicatorType.TREND, lambda data, **kwargs: cls.parabolic_sar(data, **kwargs))
        # Stochastic
        cls._indicators["stochastic"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.stochastic(data, **kwargs))
        # Keltner Channels
        cls._indicators["keltner"] = (IndicatorType.VOLATILITY, lambda data, **kwargs: cls.keltner_channels(data, **kwargs))
        # Donchian Channels
        cls._indicators["donchian"] = (IndicatorType.VOLATILITY, lambda data, **kwargs: cls.donchian_channels(data, **kwargs))
        # ROC
        cls._indicators["roc"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.roc(data, **kwargs))
        # CMO
        cls._indicators["cmo"] = (IndicatorType.MOMENTUM, lambda data, **kwargs: cls.chande_momentum(data, **kwargs))

    @classmethod
    def get_available_indicators(cls) -> List[Dict]:
        """Get list of all available indicators."""
        return [
            {"name": name, "type": info[0].value}
            for name, info in cls._indicators.items()
        ]

    @classmethod
    def sma(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Simple Moving Average.
        
        SMA = Sum(close, period) / period
        """
        return data[column].rolling(window=period).mean()

    @classmethod
    def ema(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Exponential Moving Average.
        
        EMA = close * (2 / (period + 1)) + EMA_prev * (1 - 2 / (period + 1))
        """
        return data[column].ewm(span=period, adjust=False).mean()

    @classmethod
    def wma(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Weighted Moving Average.
        
        WMA = Sum(close * weight, period) / Sum(weight, period)
        """
        weights = np.arange(1, period + 1)
        result = pd.Series(index=data.index, dtype=float)
        
        for i in range(period - 1, len(data)):
            window = data[column].iloc[i - period + 1:i + 1]
            result.iloc[i] = np.dot(window.values, weights) / weights.sum()
        
        return result

    @classmethod
    def smma(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Smoothed Moving Average.
        
        SMMAsma = (SMA_prev * (period - 1) + close) / period
        """
        result = pd.Series(index=data.index, dtype=float)
        result.iloc[:period - 1] = np.nan
        
        if len(data) >= period:
            result.iloc[period - 1] = data[column].iloc[:period].mean()
            for i in range(period, len(data)):
                result.iloc[i] = (result.iloc[i - 1] * (period - 1) + data[column].iloc[i]) / period
        
        return result

    @classmethod
    def dema(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Double Exponential Moving Average.
        
        DEMA = 2 * EMA - EMA(EMA)
        """
        ema1 = cls.ema(data, period, column)
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        return 2 * ema1 - ema2

    @classmethod
    def tema(cls, data: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """
        Triple Exponential Moving Average.
        
        TEMA = 3 * EMA - 3 * EMA(EMA) + EMA(EMA(EMA))
        """
        ema1 = cls.ema(data, period, column)
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        return 3 * ema1 - 3 * ema2 + ema3

    @classmethod
    def sma_rsi(cls, data: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
        """
        RSI using Simple Moving Average.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        delta = data[column].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    @classmethod
    def cci(cls, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Commodity Channel Index.
        
        CCI = (Typical Price - SMA(TP)) / (0.015 * Mean Deviation)
        """
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_dev = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        return (typical_price - sma_tp) / (0.015 * mean_dev)

    @classmethod
    def adx(cls, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Average Directional Index.
        
        ADX measures the strength of a trend (not direction).
        """
        high = data["high"]
        low = data["low"]
        close = data["close"]
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
        
        plus_di = 100 * cls.ema(pd.DataFrame({"value": plus_dm}), period, "value")
        minus_di = 100 * cls.ema(pd.DataFrame({"value": minus_dm}), period, "value")
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = cls.ema(pd.DataFrame({"value": dx}), period, "value")
        
        return adx

    @classmethod
    def macd(
        cls,
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = "close",
    ) -> pd.DataFrame:
        """
        MACD (Moving Average Convergence Divergence).
        
        Returns DataFrame with macd, signal, and histogram columns.
        """
        ema_fast = cls.ema(data, fast_period, column)
        ema_slow = cls.ema(data, slow_period, column)
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        })

    @classmethod
    def bollinger_bands(
        cls,
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = "close",
    ) -> pd.DataFrame:
        """
        Bollinger Bands.
        
        Returns DataFrame with upper, middle, lower, and bandwidth columns.
        """
        sma = data[column].rolling(window=period).mean()
        std = data[column].rolling(window=period).std()
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        bandwidth = ((upper - lower) / sma) * 100
        
        return pd.DataFrame({
            "upper": upper,
            "middle": sma,
            "lower": lower,
            "bandwidth": bandwidth,
        })

    @classmethod
    def atr(
        cls,
        data: pd.DataFrame,
        period: int = 14,
        smoothing: str = "rma",
    ) -> pd.Series:
        """
        Average True Range.
        
        True Range = max(H-L, abs(H-Cc), abs(L-Cc))
        """
        high = data["high"]
        low = data["low"]
        close = data["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        if smoothing == "sma":
            return tr.rolling(window=period).mean()
        elif smoothing == "ema":
            return tr.ewm(span=period, adjust=False).mean()
        else:  # rma (rolling moving average)
            result = pd.Series(index=data.index, dtype=float)
            result.iloc[:period] = np.nan
            if len(data) >= period:
                result.iloc[period - 1] = tr.iloc[:period].mean()
                for i in range(period, len(data)):
                    result.iloc[i] = (result.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period
            return result

    @classmethod
    def mfi(cls, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Money Flow Index.
        
        MFI uses price and volume to identify overbought/oversold conditions.
        """
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        raw_money_flow = typical_price * data["volume"]
        
        delta = typical_price.diff()
        positive_flow = raw_money_flow.where(delta > 0, 0)
        negative_flow = raw_money_flow.where(delta < 0, 0)
        
        avg_positive_flow = positive_flow.rolling(window=period).mean()
        avg_negative_flow = negative_flow.rolling(window=period).mean()
        
        rs = avg_positive_flow / avg_negative_flow
        mfi = 100 - (100 / (1 + rs))
        
        return mfi

    @classmethod
    def vwap(cls, data: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price.
        
        VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        """
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        cumulative_product = (typical_price * data["volume"]).cumsum()
        cumulative_volume = data["volume"].cumsum()
        
        return cumulative_product / cumulative_volume

    @classmethod
    def ichimoku(cls, data: pd.DataFrame) -> pd.DataFrame:
        """
        Ichimoku Kinko Hyo.
        
        Returns DataFrame with tenkan, kijun, senkou_a, senkou_b columns.
        """
        period_9_high = data["high"].rolling(window=9).max()
        period_9_low = data["low"].rolling(window=9).min()
        period_26_high = data["high"].rolling(window=26).max()
        period_26_low = data["low"].rolling(window=26).min()
        period_52_high = data["high"].rolling(window=52).max()
        period_52_low = data["low"].rolling(window=52).min()
        
        tenkan = (period_9_high + period_9_low) / 2
        kijun = (period_26_high + period_26_low) / 2
        senkou_a = ((kijun + cls.ema(data, 26, "close").shift(26)) / 2)
        senkou_b = ((period_52_high + period_52_low) / 2).shift(26)
        
        return pd.DataFrame({
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
        })

    @classmethod
    def parabolic_sar(
        cls,
        data: pd.DataFrame,
        af_step: float = 0.02,
        af_max: float = 0.2,
    ) -> pd.Series:
        """
        Parabolic SAR.
        
        SAR is used to determine trend direction and set stop loss levels.
        """
        n = len(data)
        sar = pd.Series(index=data.index, dtype=float)
        ep = data["high"].iloc[0]  # Extreme point
        af = af_step
        is_up_trend = True
        
        # Initial values
        sar.iloc[0] = data["low"].iloc[0]
        
        for i in range(1, n):
            if is_up_trend:
                sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])
                if data["low"].iloc[i] < sar.iloc[i]:
                    is_up_trend = False
                    sar.iloc[i] = ep
                    ep = data["low"].iloc[i]
                    af = af_step
            else:
                sar.iloc[i] = sar.iloc[i - 1] - af * (sar.iloc[i - 1] - ep)
                if data["high"].iloc[i] > sar.iloc[i]:
                    is_up_trend = True
                    sar.iloc[i] = ep
                    ep = data["high"].iloc[i]
                    af = af_step
            
            # Update extreme point and acceleration factor
            if is_up_trend:
                if data["high"].iloc[i] > ep:
                    ep = data["high"].iloc[i]
                    af = min(af + af_step, af_max)
            else:
                if data["low"].iloc[i] < ep:
                    ep = data["low"].iloc[i]
                    af = min(af + af_step, af_max)
        
        return sar

    @classmethod
    def stochastic(
        cls,
        data: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3,
    ) -> pd.DataFrame:
        """
        Stochastic Oscillator.
        
        Returns DataFrame with %K and %D columns.
        """
        low_min = data["low"].rolling(window=k_period).min()
        high_max = data["high"].rolling(window=k_period).max()
        
        k = 100 * (data["close"] - low_min) / (high_max - low_min)
        d = cls.ema(pd.DataFrame({"value": k}), d_period, "value")
        
        return pd.DataFrame({
            "k": k,
            "d": d,
        })

    @classmethod
    def keltner_channels(
        cls,
        data: pd.DataFrame,
        period: int = 20,
        atr_multiplier: float = 2.0,
    ) -> pd.DataFrame:
        """
        Keltner Channels.
        
        Returns DataFrame with upper, middle, lower columns.
        """
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        middle = typical_price.rolling(window=period).mean()
        atr_values = cls.atr(data, period)
        
        upper = middle + (atr_multiplier * atr_values)
        lower = middle - (atr_multiplier * atr_values)
        
        return pd.DataFrame({
            "upper": upper,
            "middle": middle,
            "lower": lower,
        })

    @classmethod
    def donchian_channels(
        cls,
        data: pd.DataFrame,
        period: int = 20,
    ) -> pd.DataFrame:
        """
        Donchian Channels.
        
        Returns DataFrame with upper, middle, lower columns.
        """
        upper = data["high"].rolling(window=period).max()
        lower = data["low"].rolling(window=period).min()
        middle = (upper + lower) / 2
        
        return pd.DataFrame({
            "upper": upper,
            "middle": middle,
            "lower": lower,
        })

    @classmethod
    def roc(cls, data: pd.DataFrame, period: int = 12, column: str = "close") -> pd.Series:
        """
        Rate of Change.
        
        ROC = ((Price - Price_prev) / Price_prev) * 100
        """
        return data[column].pct_change(periods=period) * 100

    @classmethod
    def chande_momentum(
        cls,
        data: pd.DataFrame,
        period: int = 14,
        column: str = "close",
    ) -> pd.Series:
        """
        Chande Momentum Oscillator.
        
        CMO = 100 * (Sum of gains - Sum of losses) / (Sum of gains + Sum of losses)
        """
        delta = data[column].diff()
        gains = delta.where(delta > 0, 0).rolling(window=period).sum()
        losses = (-delta).where(delta < 0, 0).rolling(window=period).sum()
        
        return 100 * (gains - losses) / (gains + losses)


# Initialize the registry after class definition is complete
IndicatorEngine._register()


# Convenience function for strategies
def calculate_indicators(
    data: pd.DataFrame,
    indicators: Dict[str, Tuple[str, Dict]],
) -> pd.DataFrame:
    """
    Calculate multiple indicators at once.
    
    Args:
        data: OHLCV DataFrame
        indicators: Dict of {name: (indicator_func_name, params)}
        
    Example:
        indicators = {
            "ema_fast": ("ema", {"period": 20, "column": "close"}),
            "ema_slow": ("ema", {"period": 50, "column": "close"}),
            "rsi": ("sma_rsi", {"period": 14}),
        }
        result = calculate_indicators(df, indicators)
    """
    engine = IndicatorEngine(data)
    result_df = data.copy()
    
    for name, (func_name, params) in indicators.items():
        try:
            values = engine.calculate(func_name, params)
            result_df[name] = values
        except Exception as e:
            logger.error(f"Error calculating {func_name}: {e}")
            result_df[name] = np.nan
    
    return result_df
