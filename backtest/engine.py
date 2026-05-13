"""
Backtest Engine - Historical strategy testing and analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from app.logger import get_logger
from indicators.indicators import IndicatorEngine

logger = get_logger("nobitex_trader.backtest")


@dataclass
class Trade:
    """Represents a single trade."""
    timestamp: datetime
    symbol: str
    side: str
    entry_price: float
    quantity: float
    exit_price: Optional[float] = None
    pnl: float = 0
    pnl_percent: float = 0
    commission: float = 0
    duration_seconds: float = 0
    reason: str = ""


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy_name,
            "symbol": self.symbol,
            "period": f"{self.start_date.date()} to {self.end_date.date()}",
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return_percent": self.total_return_percent,
            "max_drawdown_percent": self.max_drawdown_percent,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
        }


class BacktestEngine:
    """Backtest engine for strategy testing on historical data."""

    def __init__(self, initial_capital: float = 10000000):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital in IRT
        """
        self._initial_capital = initial_capital
        self._capital = initial_capital
        self._trades: List[Trade] = []
        self._equity: List[Dict] = []
        logger.info(f"BacktestEngine initialized with capital {initial_capital}")

    def run(
        self,
        df: pd.DataFrame,
        strategy_func,
        symbol: str = "BTCIRT",
        strategy_name: str = "custom",
        commission_rate: float = 0.0015,
    ) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            df: OHLCV DataFrame
            strategy_func: Function that generates signals from DataFrame
            symbol: Trading pair symbol
            strategy_name: Name of the strategy
            commission_rate: Commission rate per trade
            
        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"Starting backtest: {strategy_name} on {symbol}")
        
        self._capital = self._initial_capital
        self._trades = []
        self._equity = []
        
        # Run strategy simulation
        position = None
        position_size = 0.95  # Use 95% of capital
        
        for i in range(60, len(df)):
            window = df.iloc[:i+1]
            signal = strategy_func(window, i)
            
            current_price = df.iloc[i]["close"]
            current_time = df.iloc[i]["timestamp"] if "timestamp" in df.columns else datetime.now()
            
            if signal == "BUY" and position is None:
                # Enter long position
                amount = (self._capital * position_size) / current_price
                commission = amount * current_price * commission_rate
                self._capital -= amount * current_price + commission
                position = current_price
                position_size = amount
                
            elif signal == "SELL" and position is not None:
                # Exit position
                revenue = position_size * current_price
                commission = revenue * commission_rate
                pnl = revenue - commission - (position_size * position)
                self._capital += revenue - commission
                
                trade = Trade(
                    timestamp=current_time if isinstance(current_time, datetime) else datetime.now(),
                    symbol=symbol,
                    side="sell",
                    entry_price=position,
                    quantity=position_size,
                    exit_price=current_price,
                    pnl=pnl,
                    pnl_percent=((current_price - position) / position * 100) if position > 0 else 0,
                    commission=commission,
                    reason="Strategy signal",
                )
                self._trades.append(trade)
                position = None
                position_size = 0
            
            # Record equity
            equity = self._capital + (position_size * current_price if position else 0)
            self._equity.append({
                "timestamp": current_time,
                "equity": equity,
            })
        
        # Close any open position at end
        if position is not None:
            final_price = df.iloc[-1]["close"]
            final_time = df.iloc[-1]["timestamp"] if "timestamp" in df.columns else datetime.now()
            revenue = position_size * final_price
            commission = revenue * commission_rate
            pnl = revenue - commission - (position_size * position)
            self._capital += revenue - commission
            
            self._trades.append(Trade(
                timestamp=final_time if isinstance(final_time, datetime) else datetime.now(),
                symbol=symbol,
                side="sell",
                entry_price=position,
                quantity=position_size,
                exit_price=final_price,
                pnl=pnl,
                pnl_percent=((final_price - position) / position * 100) if position > 0 else 0,
                commission=commission,
                reason="Backtest close",
            ))
        
        return self._calculate_results(strategy_name, symbol)

    def _calculate_results(self, strategy_name: str, symbol: str) -> BacktestResult:
        """Calculate backtest performance metrics."""
        trades = self._trades
        total_trades = len(trades)
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        
        total_return = self._capital - self._initial_capital
        total_return_pct = (total_return / self._initial_capital * 100) if self._initial_capital > 0 else 0
        
        # Calculate drawdown
        equity_values = [e["equity"] for e in self._equity]
        peak = 0
        max_dd = 0
        max_dd_pct = 0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            if dd > max_dd_pct:
                max_dd = peak - eq
                max_dd_pct = dd
        
        # Calculate Sharpe ratio
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i-1] > 0:
                returns.append((equity_values[i] - equity_values[i-1]) / equity_values[i-1])
        
        sharpe = 0
        if returns and len(returns) > 1:
            avg_ret = np.mean(returns)
            std_ret = np.std(returns)
            if std_ret > 0:
                sharpe = (avg_ret / std_ret) * np.sqrt(252 * 24 * 4)  # Annualized (4h candles)
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = np.mean([t.pnl for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl for t in losing]) if losing else 0
        
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=self._equity[0]["timestamp"] if self._equity else datetime.now(),
            end_date=self._equity[-1]["timestamp"] if self._equity else datetime.now(),
            initial_capital=self._initial_capital,
            final_capital=self._capital,
            total_return=total_return,
            total_return_percent=total_return_pct,
            max_drawdown=max_dd,
            max_drawdown_percent=max_dd_pct,
            sharpe_ratio=sharpe,
            win_rate=len(winning) / total_trades if total_trades > 0 else 0,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=self._equity,
        )
