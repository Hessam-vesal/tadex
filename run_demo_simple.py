#!/usr/bin/env python3
"""
Simple Demo Runner - Run the trading bot in demo/paper trading mode without user interaction.
"""

import sys
import os
import asyncio
import signal
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from main import NobitexQuantTrader


def setup_demo_environment():
    """Setup environment for demo mode."""
    # Ensure we're in paper trading mode
    os.environ["TRADING_MODE"] = "paper"
    print("Demo mode activated - Paper trading enabled")


async def run_demo():
    """Run the bot in demo mode."""
    print("Starting Nobitex Quant Trader in Demo Mode")
    print("=" * 50)
    
    # Setup demo environment
    setup_demo_environment()
    
    # Get settings to show configuration
    settings = get_settings()
    print(f"Trading Mode: {settings.trading.mode.value}")
    print(f"Symbols: {', '.join(settings.trading.symbols)}")
    print(f"Timeframe: {settings.trading.timeframe.value}")
    print(f"Update Interval: {settings.data.update_interval}s")
    print(f"Risk Per Trade: {settings.trading.risk_per_trade:.2%}")
    print(f"Enabled Strategies: {', '.join(settings.strategy.enabled_strategies)}")
    print("=" * 50)
    
    # Create and start the bot
    bot = NobitexQuantTrader()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("Initializing trading bot...")
        await bot.start()
    except KeyboardInterrupt:
        print("\nManual interrupt received")
        await bot.stop()
    except Exception as e:
        print(f"Error running demo: {e}")
        import traceback
        traceback.print_exc()
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    print("Starting demo mode automatically...")
    asyncio.run(run_demo())
