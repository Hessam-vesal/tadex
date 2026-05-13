"""
Market Data Engine - Real-time market data processing and management.

Handles normalization, storage, and distribution of market data
from Nobitex exchange.
"""

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config import Timeframe, get_settings
from app.logger import get_logger, data_logger

logger = get_logger("nobitex_trader.market_data")


@dataclass
class Ticker:
    """Represents a ticker update."""
    symbol: str
    last_price: float
    best_bid: float
    best_ask: float
    high: float
    low: float
    volume: float
    volume_weighted_price: float
    timestamp: float

    @property
    def mid_price(self) -> float:
        """Calculate mid price."""
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        return self.best_ask - self.best_bid

    @property
    def spread_percent(self) -> float:
        """Calculate bid-ask spread as percentage."""
        if self.mid_price == 0:
            return 0
        return (self.spread / self.mid_price) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "last_price": self.last_price,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "vwap": self.volume_weighted_price,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_percent": self.spread_percent,
        }


@dataclass
class OrderBookLevel:
    """Represents a single level in the order book."""
    price: float
    quantity: float


@dataclass
class OrderBook:
    """Represents the order book for a symbol."""
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: float = 0

    @property
    def best_bid(self) -> Optional[float]:
        """Get best bid price."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Get best ask price."""
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        """Get mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[float]:
        """Get spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    def get_depth(self, levels: int = 10) -> Dict[str, float]:
        """Calculate order book depth."""
        bid_depth = sum(b.price * b.quantity for b in self.bids[:levels])
        ask_depth = sum(a.price * a.quantity for a in self.asks[:levels])
        return {"bid_depth": bid_depth, "ask_depth": ask_depth}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "mid_price": self.mid_price,
            "bids": [{"price": b.price, "quantity": b.quantity} for b in self.bids[:20]],
            "asks": [{"price": a.price, "quantity": a.quantity} for a in self.asks[:20]],
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


@dataclass
class Trade:
    """Represents a trade execution."""
    symbol: str
    price: float
    quantity: float
    is_buyer_maker: bool
    timestamp: float

    @property
    def side(self) -> str:
        """Get trade side."""
        return "sell" if self.is_buyer_maker else "buy"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "side": self.side,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


@dataclass
class Candle:
    """Represents OHLCV candle data."""
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int = 0

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish."""
        return self.close < self.open

    @property
    def body_size(self) -> float:
        """Calculate candle body size."""
        return abs(self.close - self.open)

    @property
    def mid_price(self) -> float:
        """Get candle mid price."""
        return (self.high + self.low) / 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp / 1000).isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trades": self.trades,
            "is_bullish": self.is_bullish,
        }

    def to_pandas(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series({
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trades": self.trades,
            "timestamp": datetime.fromtimestamp(self.timestamp / 1000),
        })


class CandleManager:
    """Manages candle aggregation from tick data."""

    def __init__(self):
        """Initialize candle manager."""
        self._current_candles: Dict[str, Candle] = {}
        self._completed_candles: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._tick_buffer: Dict[str, deque] = defaultdict(deque)

    def get_timeframe_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds."""
        timeframe_map = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
        }
        return timeframe_map.get(timeframe, 300)

    def add_tick(
        self,
        symbol: str,
        price: float,
        quantity: float,
        timestamp_ms: int,
        is_buyer_maker: bool = False,
    ) -> Optional[Candle]:
        """
        Add a tick and return completed candle if formed.
        
        Args:
            symbol: Trading pair symbol
            price: Trade price
            quantity: Trade quantity
            timestamp_ms: Trade timestamp in milliseconds
            is_buyer_maker: True if buyer is maker

        Returns:
            Completed candle if a new candle started, None otherwise
        """
        timeframe = get_settings().trading.timeframe.value
        interval_sec = self.get_timeframe_seconds(timeframe)
        candle_start_ms = (timestamp_ms // (interval_sec * 1000)) * (
            interval_sec * 1000
        )

        key = f"{symbol}_{timeframe}"
        if key not in self._current_candles:
            self._current_candles[key] = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=candle_start_ms,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=quantity,
            )
        else:
            candle = self._current_candles[key]
            candle.high = max(candle.high, price)
            candle.low = min(candle.low, price)
            candle.close = price
            candle.volume += quantity

        current_candle = self._current_candles[key]
        if current_candle.timestamp < candle_start_ms:
            completed = current_candle
            self._completed_candles[key].append(completed)

            self._current_candles[key] = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=candle_start_ms,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=quantity,
            )
            return completed

        return None

    def get_completed_candles(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> List[Candle]:
        """Get completed candles for a symbol."""
        if timeframe is None:
            timeframe = get_settings().trading.timeframe.value
        key = f"{symbol}_{timeframe}"
        candles = list(self._completed_candles.get(key, []))
        return candles[-limit:]

    def get_candles_dataframe(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get completed candles as a pandas DataFrame."""
        candles = self.get_completed_candles(symbol, timeframe, limit)
        if not candles:
            return pd.DataFrame()

        data = [c.to_dict() for c in candles]
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        ohlcv = ["open", "high", "low", "close", "volume"]
        return df[[col for col in ohlcv if col in df.columns]]

    def get_current_candle(self, symbol: str) -> Optional[Candle]:
        """Get the current (forming) candle."""
        timeframe = get_settings().trading.timeframe.value
        key = f"{symbol}_{timeframe}"
        return self._current_candles.get(key)


class MarketDataManager:
    """
    Central market data manager.
    
    Coordinates ticker updates, order book data, trades, and candle formation.
    """

    def __init__(self):
        """Initialize market data manager."""
        self._tickers: Dict[str, Ticker] = {}
        self._order_books: Dict[str, OrderBook] = {}
        self._trades: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self._candle_manager = CandleManager()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._last_update: Dict[str, float] = {}
        logger.info("MarketDataManager initialized")

    @property
    def candle_manager(self) -> CandleManager:
        """Get the candle manager."""
        return self._candle_manager

    def update_ticker(self, data: Dict[str, Any]) -> Ticker:
        """
        Process a ticker update from Nobitex.
        
        Expected format from Nobitex:
        {
            "code": "BTCIRT",
            "last": 5000000,
            "bi": 4990000,    # best bid
            "si": 5010000,    # best ask
            "h": 5100000,     # high
            "l": 4900000,     # low
            "a": 5005000,     # ask (one of asks)
            "b": 4995000,     # bid (one of bids)
            "v": 1234.56,     # volume
            "w": 5000000,     # weighted price
            "ts": 1609459200  # timestamp
        }
        """
        ticker = Ticker(
            symbol=data.get("code", data.get("symbol", "")),
            last_price=float(data.get("last", 0)),
            best_bid=float(data.get("bi", data.get("b", 0))),
            best_ask=float(data.get("si", data.get("a", 0))),
            high=float(data.get("h", 0)),
            low=float(data.get("l", 0)),
            volume=float(data.get("v", 0)),
            volume_weighted_price=float(data.get("w", 0)),
            timestamp=float(data.get("ts", time.time())),
        )

        self._tickers[ticker.symbol] = ticker
        self._last_update[ticker.symbol] = time.time()
        data_logger.debug(f"Ticker updated: {ticker.symbol} @ {ticker.last_price}")

        # Notify subscribers
        for callback in self._subscribers.get("ticker", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(ticker))
                else:
                    callback(ticker)
            except Exception as e:
                logger.error(f"Ticker subscriber error: {e}")

        return ticker

    def update_order_book(self, symbol: str, data: Dict[str, Any]):
        """
        Process order book update from Nobitex.
        
        Format:
        {
            "code": "BTCIRT",
            "buys": [{"p": 5000000, "q": 0.1}, ...],  # buys sorted ascending
            "sells": [{"p": 5010000, "q": 0.2}, ...],  # sells sorted ascending
            "ts": 1609459200
        }
        """
        book = OrderBook(
            symbol=symbol,
            bids=[
                OrderBookLevel(price=float(b["p"]), quantity=float(b["q"]))
                for b in sorted(data.get("buys", []), key=lambda x: float(x["p"]), reverse=True)
            ],
            asks=[
                OrderBookLevel(price=float(a["p"]), quantity=float(a["q"]))
                for a in sorted(data.get("sells", []), key=lambda x: float(x["p"]))
            ],
            timestamp=float(data.get("ts", time.time())),
        )
        self._order_books[symbol] = book

        # Notify subscribers
        for callback in self._subscribers.get("order_book", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(book))
                else:
                    callback(book)
            except Exception as e:
                logger.error(f"Order book subscriber error: {e}")

    def update_trade(self, data: Dict[str, Any]) -> Trade:
        """
        Process a trade update from Nobitex.
        
        Format:
        {
            "code": "BTCIRT",
            "tradeId": 12345,
            "price": 5000000,
            "amount": 0.1,
            "ts": 1609459200,
            "isBuyerMaker": true
        }
        """
        trade = Trade(
            symbol=data.get("code", data.get("symbol", "")),
            price=float(data.get("price", data.get("p", 0))),
            quantity=float(data.get("amount", data.get("q", 0))),
            is_buyer_maker=data.get("isBuyerMaker", data.get("is_buyer_maker", False)),
            timestamp=float(data.get("ts", time.time())),
        )

        self._trades[trade.symbol].append(trade)

        # Update candle manager
        completed_candle = self._candle_manager.add_tick(
            symbol=trade.symbol,
            price=trade.price,
            quantity=trade.quantity,
            timestamp_ms=int(trade.timestamp * 1000),
            is_buyer_maker=trade.is_buyer_maker,
        )

        if completed_candle:
            for callback in self._subscribers.get("candle", []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(completed_candle))
                    else:
                        callback(completed_candle)
                except Exception as e:
                    logger.error(f"Candle subscriber error: {e}")

        return trade

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current ticker for a symbol."""
        return self._tickers.get(symbol)

    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Get current order book for a symbol."""
        return self._order_books.get(symbol)

    def get_recent_trades(
        self, symbol: str, limit: int = 100
    ) -> List[Trade]:
        """Get recent trades for a symbol."""
        return list(self._trades.get(symbol, [])[-limit:])

    def get_candles(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get candles as DataFrame."""
        return self._candle_manager.get_candles_dataframe(
            symbol, timeframe, limit
        )

    def get_all_tickers(self) -> Dict[str, Ticker]:
        """Get all current tickers."""
        return dict(self._tickers)

    def get_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols."""
        return {
            symbol: ticker.last_price
            for symbol, ticker in self._tickers.items()
        }

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to market data events."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from market data events."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def get_last_update_time(self, symbol: str) -> Optional[float]:
        """Get last update time for a symbol."""
        return self._last_update.get(symbol)

    def get_data_freshness(self, symbol: str) -> float:
        """Get data freshness in seconds."""
        last_update = self._last_update.get(symbol, 0)
        if last_update == 0:
            return float("inf")
        return time.time() - last_update
