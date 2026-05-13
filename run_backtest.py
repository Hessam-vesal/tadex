#!/usr/bin/env python3
"""
Backtest Runner - Simple script to run backtests.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.engine import BacktestEngine
from strategy.examples import MomentumStrategy
from indicators.indicators import IndicatorEngine


def generate_sample_data(days: int = 30) -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    # Generate timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Generate price data with some trend and volatility
    periods = days * 24 * 4  # 15-minute candles
    timestamps = pd.date_range(start=start_time, end=end_time, periods=periods)
    
    # Generate realistic price movements
    np.random.seed(42)  # For reproducible results
    returns = np.random.normal(0.0001, 0.02, periods)  # Small drift, 2% volatility
    
    prices = [10000000]  # Start at 10,000,000 IRT (100 million toman)
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLC data
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    
    for i, price in enumerate(prices):
        open_price = price
        close_price = prices[min(i + 1, len(prices) - 1)]
        
        # Generate realistic OHLC
        high = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
        
        opens.append(open_price)
        highs.append(high)
        lows.append(low)
        closes.append(close_price)
        volumes.append(np.random.uniform(1, 100))  # Random volume
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df


def simple_momentum_strategy(df, index):
    """Simple momentum strategy for backtesting."""
    if index < 20:
        return None
    
    # Simple moving average crossover
    fast_ma = df['close'].iloc[index-10:index].mean()
    slow_ma = df['close'].iloc[index-20:index].mean()
    
    if fast_ma > slow_ma:
        return "BUY"
    elif fast_ma < slow_ma:
        return "SELL"
    
    return None


def run_backtest():
    """Run a simple backtest."""
    print("Generating sample data...")
    df = generate_sample_data(days=7)
    print(f"Generated {len(df)} candles")
    
    print("Initializing backtest engine...")
    engine = BacktestEngine(initial_capital=10000000)  # 10 million IRT
    
    print("Running backtest...")
    result = engine.run(
        df=df,
        strategy_func=simple_momentum_strategy,
        symbol="BTCIRT",
        strategy_name="sample_momentum",
        commission_rate=0.0015  # 0.15% commission
    )
    
    print("\n" + "="*50)
    print("BACKTEST RESULTS")
    print("="*50)
    print(f"Strategy: {result.strategy_name}")
    print(f"Symbol: {result.symbol}")
    print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
    print(f"Initial Capital: {result.initial_capital:,.0f} IRT")
    print(f"Final Capital: {result.final_capital:,.0f} IRT")
    print(f"Total Return: {result.total_return_percent:+.2f}%")
    print(f"Max Drawdown: {result.max_drawdown_percent:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Win Rate: {result.win_rate:.2%}")
    print(f"Total Trades: {result.total_trades}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Average Win: {result.avg_win:,.0f} IRT")
    print(f"Average Loss: {result.avg_loss:,.0f} IRT")
    
    if result.trades:
        print(f"\nFirst 5 trades:")
        for i, trade in enumerate(result.trades[:5]):
            print(f"  {trade.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                  f"{trade.side.upper()} {trade.quantity:.6f} @ {trade.entry_price:,.0f} "
                  f"-> {trade.exit_price:,.0f} (PnL: {trade.pnl:+,.0f})")
    
    return result


if __name__ == "__main__":
    try:
        result = run_backtest()
        print(f"\nBacktest completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
