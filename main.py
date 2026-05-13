"""
Nobitex Quant Trader - Main Trading Bot

Professional quantitative trading system for Nobitex exchange.
Implements multi-strategy trading with comprehensive risk management.
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.logger import get_logger

from core.event_engine import EventEngine, Event
from core.scheduler import Scheduler
from data.market_data import MarketDataManager
from indicators.indicators import IndicatorEngine
from strategy.strategy_manager import StrategyManager, StrategyFactory
from strategy.base_strategy import Signal, TradingSignal
from risk.risk_manager import RiskManager, RiskDecision, Position
from execution.engine import ExecutionEngine, OrderSide, OrderType
from portfolio.manager import PortfolioManager
from backtest.engine import BacktestEngine
from notification.alerts import NotificationManager
from database.repository import TradeRepository
from data.websocket_client import NobitexWebSocketClient


# Import strategies to register them with the factory
import strategy.examples

logger = get_logger("nobitex_trader.main")


class NobitexQuantTrader:
    """
    Main trading bot that orchestrates all components.
    
    Architecture:
    - MarketDataService: Fetches market data via WebSocket
    - StrategyManager: Generates trading signals
    - RiskManager: Validates trades against risk parameters
    - ExecutionEngine: Places and manages orders
    - PortfolioManager: Tracks portfolio state
    - NotificationManager: Sends alerts to user
    """

    def __init__(self):
        """Initialize the trading bot."""
        self._settings = get_settings()
        self._running = False
        self._stop_event = asyncio.Event()

        # Initialize components
        self._event_engine = EventEngine()
        self._scheduler = Scheduler()
        self._market_data = MarketDataManager()
        self._strategy_manager = StrategyManager()
        self._risk_manager = RiskManager()
        self._execution_engine = ExecutionEngine()
        self._portfolio_manager = PortfolioManager()
        self._notification = NotificationManager()
        self._database = TradeRepository()
        self._websocket = NobitexWebSocketClient(self._market_data)


        logger.info("NobitexQuantTrader initialized")

    async def start(self):
        """Start the trading bot."""
        logger.info("Starting Nobitex Quant Trader...")
        self._running = True

        # Initialize components
        await self._initialize()

        # Register periodic tasks
        self._scheduler.schedule_interval(
            "market_data_fetch",
            self._process_market_data,
            interval_seconds=self._settings.data.update_interval,
            async_task=True,
        )
        self._scheduler.schedule_interval(
            "portfolio_update",
            self._update_portfolio,
            interval_seconds=30,
            async_task=True,
        )
        self._scheduler.schedule_interval(
            "risk_check",
            self._check_risk,
            interval_seconds=60,
            async_task=True,
        )
        
        # Start the scheduler
        self._scheduler.start()

        logger.info("Trading bot started successfully")

        # Wait for stop signal
        await self._stop_event.wait()

    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping Nobitex Quant Trader...")
        self._running = False
        self._stop_event.set()

        # Cancel all active orders
        await self._execution_engine.cancel_all_orders()

        # Send shutdown notification
        await self._notification.send_alert("🛑 Trading bot stopped")

        logger.info("Trading bot stopped")

    async def _initialize(self):
        """Initialize all components."""
        # Initialize strategy manager
        enabled_strategies = self._settings.strategy.enabled_strategies
        logger.info(f"Enabled strategies: {enabled_strategies}")

        # Initialize strategies
        for strategy_name in enabled_strategies:
            try:
                from strategy.strategy_manager import StrategyFactory
                strategy = StrategyFactory.create(strategy_name)
                self._strategy_manager.register_strategy(strategy)
                logger.info(f"Strategy '{strategy_name}' registered successfully")
            except Exception as e:
                logger.error(f"Failed to register strategy '{strategy_name}': {e}")

        # Initialize market data service
        symbols = self._settings.trading.symbols
        logger.info(f"Market data service ready for {len(symbols)} symbols: {symbols}")
        # Start WebSocket market data
        await self._websocket.start()

        # Subscribe to channels
        await self._websocket.subscribe("ticker", symbols)
        await self._websocket.subscribe("trade", symbols)
        await self._websocket.subscribe("order_book", symbols)


    async def _process_market_data(self):
        """Process incoming market data and generate signals."""
        symbols = self._settings.trading.symbols

        for symbol in symbols:
            try:
                # Get latest candles
                df = self._market_data.get_candles(symbol, limit=100)
                if df is None or len(df) == 0:
                    continue

                # Generate signals from all strategies
                signals = self._strategy_manager.generate_signals(symbol)

                for signal in signals:
                    await self._process_signal(signal)

            except Exception as e:
                logger.error(f"Error processing market data for {symbol}: {e}")

    async def _process_signal(self, signal: TradingSignal):
        """Process a trading signal through risk management."""
        # Assess risk
        assessment = self._risk_manager.assess_trade(
            symbol=signal.symbol,
            side=signal.signal.value,
            price=signal.price,
            quantity=signal.quantity,
            indicators=signal.metadata,
        )

        if assessment.decision == RiskDecision.REJECT:
            logger.warning(f"Trade rejected: {assessment.reason}")
            await self._notification.send_risk_alert(
                assessment.reason, "high"
            )
            return

        if assessment.decision == RiskDecision.WAIT:
            logger.debug(f"Trade delayed: {assessment.reason}")
            return

        # Determine quantity
        quantity = (
            assessment.suggested_quantity
            if assessment.suggested_quantity
            else signal.quantity
        )

        # Execute trade
        order = await self._execution_engine.create_and_submit(
            symbol=signal.symbol,
            side=OrderSide(signal.signal.value),
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=signal.price,
            strategy_name=signal.strategy_name,
        )

        if order:
            # Add position
            position = Position(
                symbol=signal.symbol,
                side=signal.signal.value,
                entry_price=signal.price,
                quantity=quantity,
                entry_time=datetime.now(),
                stop_loss=assessment.suggested_stop_loss,
                take_profit=assessment.suggested_take_profit,
            )
            self._risk_manager.add_position(position)

            # Record in database
            self._database.save_trade({
                "symbol": signal.symbol,
                "side": signal.signal.value,
                "price": signal.price,
                "quantity": quantity,
                "strategy": signal.strategy_name,
            })

            # Send notification
            await self._notification.send_trade_alert({
                "symbol": signal.symbol,
                "side": signal.signal.value,
                "quantity": quantity,
                "price": signal.price,
                "commission": order.commission,
            })

            logger.info(
                f"Trade executed: {signal.signal.value} "
                f"{quantity} {signal.symbol} @ {signal.price:,.0f}"
            )

    async def _update_portfolio(self):
        """Update portfolio state."""
        try:
            snapshot = self._portfolio_manager.take_snapshot()
            logger.debug(f"Portfolio snapshot: {snapshot.total_value:,.0f} IRT")
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")

    async def _check_risk(self):
        """Check risk parameters and pause if needed."""
        try:
            summary = self._risk_manager.get_risk_summary()
            drawdown = summary.get("current_drawdown", 0)
            max_drawdown = self._settings.trading.max_drawdown

            if drawdown >= max_drawdown:
                logger.warning(
                    f"Drawdown limit reached: {drawdown:.2%} >= {max_drawdown:.2%}"
                )
                self._risk_manager.pause_trading()
                await self._notification.send_risk_alert(
                    f"Maximum drawdown reached: {drawdown:.2%}",
                    "critical",
                )
        except Exception as e:
            logger.error(f"Error checking risk: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        return {
            "running": self._running,
            "start_time": datetime.now().isoformat(),
            "strategies": self._strategy_manager.get_strategy_status(),
            "risk": self._risk_manager.get_risk_summary(),
            "portfolio": self._portfolio_manager.get_performance(),
            "execution": self._execution_engine.get_stats(),
            "notifications": self._notification.get_stats(),
            "database": self._database.get_stats(),
        }


# Signal handler for graceful shutdown
def _signal_handler(bot: NobitexQuantTrader, signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(bot.stop())


# Main entry point
async def main():
    """Main entry point for the trading bot."""
    bot = NobitexQuantTrader()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda s, f: asyncio.create_task(bot.stop()))

    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
