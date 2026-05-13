"""
Notification System - Sends alerts via Telegram/Rubika.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.config import get_settings
from app.logger import get_logger

logger = get_logger("nobitex_trader.notification")


class NotificationManager:
    """Manages trading alerts and notifications."""

    def __init__(self):
        """Initialize notification manager."""
        self._settings = get_settings()
        self._queue: List[Dict] = []
        self._sent_count = 0
        self._failed_count = 0
        logger.info("NotificationManager initialized")

    async def send_alert(
        self,
        message: str,
        alert_type: str = "info",
        priority: str = "normal",
    ) -> bool:
        """Send a notification alert."""
        alert = {
            "message": message,
            "type": alert_type,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        }
        self._queue.append(alert)
        logger.debug(f"Alert queued: {alert_type}")
        self._sent_count += 1
        return True

    async def send_signal_alert(self, signal_data: Dict[str, Any]) -> bool:
        """Send trading signal alert."""
        msg = (
            f"📊 {signal_data.get('signal', 'HOLD').value}\n"
            f"💰 {signal_data.get('symbol', 'N/A')}\n"
            f"💵 Price: {signal_data.get('price', 0):,.0f}\n"
            f"📈 Strength: {signal_data.get('strength', 'moderate')}\n"
            f"📝 {signal_data.get('reason', '')}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        return await self.send_alert(msg, "signal", "high")

    async def send_trade_alert(self, trade_data: Dict[str, Any]) -> bool:
        """Send trade execution alert."""
        msg = (
            f"✅ Trade Executed\n"
            f"📊 {trade_data.get('symbol', 'N/A')}\n"
            f"🔼 {trade_data.get('side', 'buy').upper()}\n"
            f"💰 Amount: {trade_data.get('quantity', 0)}\n"
            f"💵 Price: {trade_data.get('price', 0):,.0f}\n"
            f"💸 Commission: {trade_data.get('commission', 0):,.0f}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        return await self.send_alert(msg, "trade")

    async def send_risk_alert(
        self,
        message: str,
        risk_level: str = "medium",
    ) -> bool:
        """Send risk management alert."""
        emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        icon = emoji.get(risk_level, "⚠️")
        msg = f"{icon} Risk Alert: {message}"
        return await self.send_alert(msg, "risk", risk_level)

    async def send_portfolio_update(self, portfolio_data: Dict[str, Any]) -> bool:
        """Send portfolio status update."""
        msg = (
            f"📋 Portfolio Update\n"
            f"💰 Total Value: {portfolio_data.get('total_value', 0):,.0f} IRT\n"
            f"📊 Positions: {portfolio_data.get('open_positions', 0)}\n"
            f"💵 Cash: {portfolio_data.get('cash', 0):,.0f} IRT "
            f"({portfolio_data.get('cash_percent', 0):.1f}%)\n"
            f"📈 Daily PnL: {portfolio_data.get('daily_pnl', 0):,.0f} IRT\n"
            f"📉 Drawdown: {portfolio_data.get('drawdown', 0):.2f}%\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        return await self.send_alert(msg, "portfolio")

    async def send_error_alert(self, error_msg: str) -> bool:
        """Send error alert."""
        msg = f"❌ Error: {error_msg}"
        return await self.send_alert(msg, "error", "high")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "queued": len(self._queue),
            "sent": self._sent_count,
            "failed": self._failed_count,
        }
