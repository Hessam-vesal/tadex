"""
Risk Manager - Institutional-level risk management system.

Implements comprehensive risk controls including:
- Position sizing
- Portfolio exposure limits
- Drawdown protection
- Stop loss and take profit
- Daily loss limits
- Cooldown periods
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import get_settings, RiskConfig
from app.logger import get_logger, risk_logger

logger = get_logger("nobitex_trader.risk")


class RiskDecision(str, Enum):
    """Risk management decision."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    WAIT = "WAIT"


class RiskLevel(str, Enum):
    """Risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Assessment of a trade request."""
    decision: RiskDecision
    risk_level: RiskLevel
    reason: str
    suggested_quantity: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    max_allowed_loss: float = 0
    current_exposure: float = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: bool = False
    trailing_distance: float = 0.01
    highest_price: float = 0
    lowest_price: float = 0
    unrealized_pnl: float = 0
    realized_pnl: float = 0

    @property
    def notional_value(self) -> float:
        """Get notional value of position."""
        return self.entry_price * self.quantity

    @property
    def pnl_percent(self) -> float:
        """Get PnL as percentage."""
        if self.side == "long":
            return ((self.entry_price - self.entry_price) / self.entry_price) * 100
        return 0

    def update_price(self, current_price: float):
        """Update position with current price."""
        if self.side == "long":
            self.highest_price = max(self.highest_price, current_price)
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.lowest_price = min(self.lowest_price, current_price)
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity

        # Update trailing stop if enabled
        if self.trailing_stop:
            if self.side == "long" and self.highest_price > 0:
                self.stop_loss = self.highest_price * (1 - self.trailing_distance)
            elif self.side == "short" and self.lowest_price > 0:
                self.stop_loss = self.lowest_price * (1 + self.trailing_distance)


class PositionSizer:
    """Calculates optimal position sizes."""

    @staticmethod
    def fixed_quantity(
        balance: float, price: float, risk_percent: float = 0.01
    ) -> float:
        """Fixed quantity based on balance."""
        return (balance * risk_percent) / price

    @staticmethod
    def Kelly_criterion(
        win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """
        Kelly Criterion position sizing.
        
        Kelly % = W - [(1-W) / R]
        Where W = win rate, R = win/loss ratio
        """
        if avg_loss == 0:
            return 0
        ratio = avg_win / avg_loss
        kelly = win_rate - ((1 - win_rate) / ratio)
        # Use half-Kelly for safety
        return max(0, kelly * 0.5)

    @staticmethod
    def ATR_based(
        balance: float, price: float, atr: float, risk_percent: float = 0.02
    ) -> float:
        """
        ATR-based position sizing.
        
        Position size based on volatility (ATR).
        """
        if atr == 0:
            return 0
        risk_amount = balance * risk_percent
        position_size = risk_amount / (atr * 2)  # 2x ATR risk
        return max(0, position_size)

    @staticmethod
    def volatility_adjusted(
        balance: float, price: float, volatility: float, 
        max_risk: float = 0.02
    ) -> float:
        """
        Volatility-adjusted position sizing.
        
        Reduces size for high volatility assets.
        """
        if volatility == 0:
            return 0
        # Inverse volatility weighting
        base_size = (balance * max_risk) / price
        avg_volatility = 0.02  # 2% average volatility
        adjustment = avg_volatility / volatility
        return base_size * min(adjustment, 2.0)  # Cap at 2x


class RiskManager:
    """
    Main risk management engine.
    
    Validates all trades against risk parameters before execution.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        """Initialize risk manager."""
        self._config = config or get_settings().risk
        self._positions: Dict[str, Position] = {}
        self._trade_history: List[Dict[str, Any]] = []
        self._daily_pnl: float = 0
        self._daily_trades: int = 0
        self._daily_losses: int = 0
        self._last_loss_time: Optional[datetime] = None
        self._equity_curve: List[float] = []
        self._peak_equity: float = 0
        self._is_paused = False
        
        # Position sizing
        self._position_sizer = PositionSizer()
        
        logger.info("RiskManager initialized")

    def assess_trade(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        current_pnl: float = 0,
        indicators: Optional[Dict] = None,
    ) -> RiskAssessment:
        """
        Assess a trade request against risk parameters.
        
        Args:
            symbol: Trading pair
            side: buy or sell
            price: Entry price
            quantity: Trade quantity
            current_pnl: Current unrealized PnL
            indicators: Technical indicators data
            
        Returns:
            RiskAssessment with decision
        """
        if self._is_paused:
            return RiskAssessment(
                decision=RiskDecision.WAIT,
                risk_level=RiskLevel.CRITICAL,
                reason="Trading paused due to risk limits",
            )

        metrics = {}
        
        # Check 1: Maximum positions
        if len(self._positions) >= self._config.max_positions:
            return RiskAssessment(
                decision=RiskDecision.REJECT,
                risk_level=RiskLevel.HIGH,
                reason=f"Maximum positions reached ({self._config.max_positions})",
                metrics=metrics,
            )

        # Check 2: Calculate position value and exposure
        position_value = price * quantity
        total_exposure = self._calculate_total_exposure()
        new_exposure = total_exposure + position_value
        
        # Check 3: Single asset exposure limit
        asset_exposure = self._get_asset_exposure(symbol)
        if asset_exposure > self._config.max_single_asset_exposure:
            return RiskAssessment(
                decision=RiskDecision.REJECT,
                risk_level=RiskLevel.HIGH,
                reason=f"Single asset exposure limit exceeded for {symbol}",
                suggested_quantity=self._calculate_max_quantity(
                    symbol, price, asset_exposure
                ),
                metrics={
                    "current_exposure": asset_exposure,
                    "limit": self._config.max_single_asset_exposure,
                },
            )

        # Check 4: Maximum drawdown
        current_drawdown = self._calculate_current_drawdown()
        if current_drawdown >= self._config.max_drawdown:
            return RiskAssessment(
                decision=RiskDecision.REJECT,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Maximum drawdown reached ({current_drawdown:.1%})",
                metrics={"current_drawdown": current_drawdown},
            )

        # Check 5: Daily loss limit
        if self._daily_pnl < 0:
            daily_loss_percent = abs(self._daily_pnl)
            if daily_loss_percent >= self._config.daily_loss_limit:
                return RiskAssessment(
                    decision=RiskDecision.REJECT,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Daily loss limit reached",
                    metrics={"daily_pnl": self._daily_pnl},
                )

        # Check 6: Cooldown period after loss
        if self._last_loss_time:
            elapsed = (datetime.now() - self._last_loss_time).total_seconds()
            if elapsed < self._config.cooldown_period:
                remaining = self._config.cooldown_period - elapsed
                return RiskAssessment(
                    decision=RiskDecision.WAIT,
                    risk_level=RiskLevel.MEDIUM,
                    reason=f"In cooldown period, {remaining:.0f}s remaining",
                    metrics={"cooldown_remaining": remaining},
                )

        # Check 7: Risk per trade
        risk_amount = position_value * self._config.risk_per_trade
        if risk_amount > self._config.max_risk_per_trade_usd:
            suggested_qty = self._config.max_risk_per_trade_usd / (price * self._config.risk_per_trade)
            return RiskAssessment(
                decision=RiskDecision.MODIFY,
                risk_level=RiskLevel.MEDIUM,
                reason="Risk per trade exceeds limit",
                suggested_quantity=suggested_qty,
                metrics={"requested_risk": risk_amount},
            )

        # All checks passed - calculate suggested levels
        suggested_sl, suggested_tp = self._calculate_sl_tp(
            price, side, indicators
        )

        return RiskAssessment(
            decision=RiskDecision.APPROVE,
            risk_level=self._assess_trade_risk(price, quantity, indicators),
            reason="Trade approved by risk manager",
            suggested_stop_loss=suggested_sl,
            suggested_take_profit=suggested_tp,
            max_allowed_loss=position_value * self._config.risk_per_trade,
            current_exposure=new_exposure,
            metrics=metrics,
        )

    def add_position(self, position: Position):
        """Add a position to track."""
        self._positions[position.symbol] = position
        risk_logger.info(
            f"Position added: {position.symbol} {position.side} "
            f"@ {position.entry_price} x {position.quantity}"
        )

    def remove_position(self, symbol: str):
        """Remove a position."""
        if symbol in self._positions:
            del self._positions[symbol]
            risk_logger.info(f"Position removed: {symbol}")

    def update_position(self, symbol: str, current_price: float):
        """Update position with current price."""
        if symbol in self._positions:
            self._positions[symbol].update_price(current_price)

    def check_stop_loss_take_profit(
        self, symbol: str, current_price: float
    ) -> Optional[str]:
        """
        Check if stop loss or take profit triggered.
        
        Returns:
            "stop_loss", "take_profit", or None
        """
        if symbol not in self._positions:
            return None

        position = self._positions[symbol]

        if position.side == "long":
            if position.stop_loss and current_price <= position.stop_loss:
                return "stop_loss"
            if position.take_profit and current_price >= position.take_profit:
                return "take_profit"
        else:  # short
            if position.stop_loss and current_price >= position.stop_loss:
                return "stop_loss"
            if position.take_profit and current_price <= position.take_profit:
                return "take_profit"

        return None

    def record_trade_result(self, pnl: float, symbol: str):
        """Record the result of a closed trade."""
        self._daily_pnl += pnl
        self._daily_trades += 1

        if pnl < 0:
            self._daily_losses += 1
            self._last_loss_time = datetime.now()

        self._trade_history.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "pnl": pnl,
            "daily_pnl": self._daily_pnl,
        })

    def reset_daily(self):
        """Reset daily counters."""
        self._daily_pnl = 0
        self._daily_trades = 0
        self._daily_losses = 0
        logger.info("Daily risk counters reset")

    def pause_trading(self):
        """Pause all trading."""
        self._is_paused = True
        risk_logger.warning("RiskManager: Trading paused")

    def resume_trading(self):
        """Resume trading."""
        self._is_paused = False
        risk_logger.info("RiskManager: Trading resumed")

    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions."""
        return dict(self._positions)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position."""
        return self._positions.get(symbol)

    def get_total_exposure(self) -> float:
        """Get total portfolio exposure."""
        return self._calculate_total_exposure()

    def get_current_drawdown(self) -> float:
        """Get current drawdown percentage."""
        return self._calculate_current_drawdown()

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        positions_value = sum(p.notional_value for p in self._positions.values())
        
        return {
            "open_positions": len(self._positions),
            "total_exposure": positions_value,
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trades,
            "daily_losses": self._daily_losses,
            "win_rate": (
                (self._daily_trades - self._daily_losses) / max(self._daily_trades, 1)
            ),
            "max_positions": self._config.max_positions,
            "max_drawdown": self._config.max_drawdown,
            "current_drawdown": self._calculate_current_drawdown(),
            "daily_loss_limit": self._config.daily_loss_limit,
            "is_paused": self._is_paused,
        }

    def _calculate_total_exposure(self) -> float:
        """Calculate total portfolio exposure."""
        return sum(p.notional_value for p in self._positions.values())

    def _get_asset_exposure(self, symbol: str) -> float:
        """Get exposure for a specific asset."""
        total = 0
        for pos in self._positions.values():
            if pos.symbol == symbol:
                total += pos.notional_value
        return total

    def _calculate_max_quantity(
        self, symbol: str, price: float, current_exposure: float
    ) -> float:
        """Calculate maximum allowed quantity for an asset."""
        balance = 10000  # Default balance, should come from wallet
        max_exposure = balance * self._config.max_single_asset_exposure
        remaining = max(0, max_exposure - current_exposure)
        return remaining / price if price > 0 else 0

    def _calculate_current_drawdown(self) -> float:
        """Calculate current portfolio drawdown."""
        current_equity = self._calculate_total_exposure()
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
        if self._peak_equity == 0:
            return 0
        return (self._peak_equity - current_equity) / self._peak_equity

    def _calculate_sl_tp(
        self,
        price: float,
        side: str,
        indicators: Optional[Dict],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate suggested stop loss and take profit."""
        sl = None
        tp = None

        if indicators:
            atr = indicators.get("atr")
            if atr and atr > 0:
                if side == "buy":
                    sl = price * (1 - 2 * atr / price)
                    tp = price * (1 + 3 * atr / price)
                else:
                    sl = price * (1 + 2 * atr / price)
                    tp = price * (1 - 3 * atr / price)
            else:
                # Default based on config
                if side == "buy":
                    sl = price * (1 - self._config.default_stop_loss)
                    tp = price * (1 + self._config.default_take_profit)
                else:
                    sl = price * (1 + self._config.default_stop_loss)
                    tp = price * (1 - self._config.default_take_profit)
        else:
            # Default levels
            if side == "buy":
                sl = price * (1 - self._config.default_stop_loss)
                tp = price * (1 + self._config.default_take_profit)
            else:
                sl = price * (1 + self._config.default_stop_loss)
                tp = price * (1 - self._config.default_take_profit)

        return sl, tp

    def _assess_trade_risk(
        self, price: float, quantity: float, indicators: Optional[Dict]
    ) -> RiskLevel:
        """Assess the risk level of a trade."""
        position_value = price * quantity
        risk_amount = position_value * self._config.risk_per_trade
        
        if risk_amount > self._config.max_risk_per_trade_usd * 0.8:
            return RiskLevel.HIGH
        elif risk_amount > self._config.max_risk_per_trade_usd * 0.5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
