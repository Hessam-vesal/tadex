"""
Professional configuration system for Nobitex Quant Trader
Production‑grade settings management using Pydantic v2
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


class Timeframe(str, Enum):
    MIN_1 = "1m"
    MIN_3 = "3m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"


# -------------------------
# Nobitex
# -------------------------

class NobitexConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NOBITEX_",
        extra="ignore"
    )

    api_key: str = Field(default="")
    secret: str = Field(default="")

    base_url: str = "https://apiv2.nobitex.ir"
    ws_url: str = "wss://ws.nobitex.ir/connection/websocket"

    rate_limit: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret)


# -------------------------
# Rubika
# -------------------------

class RubikaConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RUBIKA_",
        extra="ignore"
    )

    token: str = ""
    chat_id: str = ""

    base_url: str = "https://botapi.rubika.ir/v3"

    def send_message_url(self) -> str:
        return f"{self.base_url}/{self.token}/sendMessage"

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)


# -------------------------
# Trading
# -------------------------

class TradingConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    mode: TradingMode = Field(default=TradingMode.PAPER, alias="TRADING_MODE")

    symbols: List[str] = Field(default=["BTCIRT", "ETHIRT"], alias="SYMBOLS")

    timeframe: Timeframe = Field(default=Timeframe.MIN_1, alias="TIMEFRAME")

    risk_per_trade: float = Field(
        default=0.01,
        alias="RISK_PER_TRADE",
        ge=0,
        le=1
    )

    max_drawdown: float = Field(
        default=0.15,
        alias="MAX_DRAWDOWN",
        ge=0,
        le=1
    )

    max_portfolio_exposure: float = Field(
        default=0.8,
        alias="MAX_PORTFOLIO_EXPOSURE",
        ge=0,
        le=1
    )

    default_stop_loss: float = 0.02
    default_take_profit: float = 0.04

    trailing_stop: bool = False
    trailing_stop_distance: float = 0.01

    @field_validator("symbols", mode="before")
    @classmethod
    def parse_symbols(cls, v):

        if isinstance(v, str):
            return [s.strip() for s in v.split(",")]

        return v


# -------------------------
# Strategy
# -------------------------

class StrategyConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    enabled_strategies: List[str] = ["momentum", "mean_reversion"]

    strategy_params: Dict[str, Any] = {}


# -------------------------
# Data
# -------------------------

class DataConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    candles_history_days: int = 30

    data_dir: Path = BASE_DIR / "data"

    update_interval: int = 5


# -------------------------
# Risk
# -------------------------

class RiskConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    max_positions: int = 5

    max_drawdown: float = 0.15

    max_risk_per_trade_usd: float = 100

    max_single_asset_exposure: float = 0.3

    daily_loss_limit: float = 0.05

    cooldown_period: int = 300

    default_stop_loss: float = 0.02

    default_take_profit: float = 0.04


# -------------------------
# Dashboard
# -------------------------

class DashboardConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DASHBOARD_",
        extra="ignore"
    )

    host: str = "0.0.0.0"

    port: int = 8080

    refresh_interval: int = 5


# -------------------------
# Logging
# -------------------------

class LoggingConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOG_",
        extra="ignore"
    )

    level: str = "INFO"

    log_file: Path = BASE_DIR / "logs/bot.log"

    max_bytes: int = 10_485_760

    backup_count: int = 5


# -------------------------
# Database
# -------------------------

class DatabaseConfig(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    path: Path = BASE_DIR / "database/trading.db"

    echo: bool = False


# -------------------------
# Root Settings
# -------------------------

class Settings:

    def __init__(self):

        self.nobitex = NobitexConfig()
        self.rubika = RubikaConfig()

        self.trading = TradingConfig()
        self.strategy = StrategyConfig()

        self.data = DataConfig()
        self.risk = RiskConfig()

        self.dashboard = DashboardConfig()
        self.logging = LoggingConfig()

        self.database = DatabaseConfig()
    

    def is_live(self):

        return self.trading.mode == TradingMode.LIVE

    def is_paper(self):

        return self.trading.mode == TradingMode.PAPER

settings = Settings()

_settings: Optional[Settings] = None


def get_settings() -> Settings:

    global _settings

    if _settings is None:

        load_dotenv()

        _settings = Settings()

    return _settings


def reset_settings():

    global _settings
    _settings = None
