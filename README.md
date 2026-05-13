<<<<<<< HEAD
# 🚀 Nobitex Quant Trader

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

**A professional quantitative trading system for the Nobitex Iranian cryptocurrency exchange.**

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Strategies](#-strategies)
- [Risk Management](#-risk-management)
- [Backtesting](#-backtesting)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Capabilities
- **Multi-Strategy Trading**: Run multiple trading strategies simultaneously
- **Real-time Market Data**: WebSocket integration for live price feeds
- **Technical Indicators**: 20+ indicators (EMA, SMA, RSI, MACD, Bollinger Bands, ATR, etc.)
- **Advanced Risk Management**: Position sizing, drawdown limits, daily loss limits, cooldown periods
- **Backtesting Engine**: Test strategies on historical data with comprehensive metrics
- **Order Management**: Smart order routing with retry logic and slippage protection
- **Portfolio Management**: Real-time portfolio tracking and allocation management
- **Notification System**: Alerts via Telegram/Rubika for trades and risk events
- **Database Persistence**: Trade and signal history storage
- **Event-driven Architecture**: Scalable and modular design

### Risk Management Features
- ✅ Maximum position limits
- ✅ Single asset exposure caps
- ✅ Maximum drawdown protection
- ✅ Daily loss limits
- ✅ Cooldown periods after losses
- ✅ Dynamic position sizing (Kelly Criterion, ATR-based, Volatility-adjusted)
- ✅ Trailing stop losses
- ✅ Automatic trade pause on risk breaches

### Built-in Strategies
- 📈 **Momentum Strategy**: EMA crossover + MACD + RSI
- 📊 **Mean Reversion Strategy**: Bollinger Bands + RSI
- 📉 **Moving Average Crossover**: Simple SMA crossover

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Nobitex Quant Trader                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Market     │  │   Strategy   │  │    Risk      │          │
│  │   Data       │─►│   Engine     │─►│   Manager    │          │
│  │   Service    │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│       ▲                    ▲                  │                  │
│       │                    │                  ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   WebSocket  │  │   Strategy   │  │   Execution  │          │
│  │   Client     │  │   Manager    │  │   Engine     │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│       ▲                    ▲                  │                  │
│       │                    │                  ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Scheduler  │  │   Event      │  │   Portfolio  │          │
│  │              │  │   Engine     │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│                                             │                   │
│                          ┌──────────────────┼──────────────┐   │
│                          │                  │              │   │
│                    ┌─────▼─────┐   ┌────────▼──────┐  ┌───▼──────┐
│                    │  Risk     │   │  Notification │  │ Database │
│                    │  Manager  │   │   Manager     │  │          │
│                    └───────────┘   └───────────────┘  └──────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
nobitex-quant-trader/
├── main.py                    # Main trading bot entry point
├── app/                       # Application core
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── logger.py              # Logging system
│   └── security.py            # Encryption for API keys
├── core/                      # Core infrastructure
│   ├── __init__.py
│   ├── event_engine.py        # Event-driven architecture
│   └── scheduler.py           # Task scheduling
├── data/                      # Data layer
│   ├── __init__.py
│   ├── market_data.py         # Market data service
│   └── websocket_client.py    # WebSocket client
├── indicators/                # Technical indicators
│   └── indicators.py          # 20+ TA indicators
├── strategy/                  # Strategy engine
│   ├── __init__.py
│   ├── base_strategy.py       # Abstract strategy class
│   ├── examples.py            # Example strategies
│   └── strategy_manager.py    # Strategy lifecycle management
├── risk/                      # Risk management
│   ├── __init__.py
│   └── risk_manager.py        # Risk assessment & controls
├── execution/                 # Order execution
│   ├── __init__.py
│   └── engine.py              # Order management
├── portfolio/                 # Portfolio management
│   └── manager.py             # Portfolio tracking
├── backtest/                  # Backtesting
│   └── engine.py              # Historical testing engine
├── notification/              # Notifications
│   ├── __init__.py
│   └── alerts.py              # Alert system
├── database/                  # Data persistence
│   ├── __init__.py
│   └── repository.py          # Trade/signal storage
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Nobitex exchange API credentials

### Quick Install

```bash
# Clone the repository
cd nobitex-quant-trader

# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp .env.example .env
```

### Edit Configuration

Open `.env` and configure your settings:

```env
# Exchange API
NOBITEX_API_KEY=your_api_key_here
NOBITEX_API_SECRET=your_api_secret_here

# Trading settings
TRADING_SYMBOLS=BTCIRT,ETHIRT,XRPIRT
TRADING_STRATEGIES=momentum,mean_reversion
TRADE_PERCENTAGE_OF_BALANCE=0.8

# Risk management
RISK_PER_TRADE=0.02
MAX_DRAWDOWN=0.15
MAX_POSITIONS=5
DAILY_LOSS_LIMIT=0.05

# Telegram notification
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NOBITEX_API_KEY` | Nobitex API key | Required |
| `NOBITEX_API_SECRET` | Nobitex API secret | Required |
| `TRADING_SYMBOLS` | Comma-separated trading pairs | `BTCIRT` |
| `TRADING_STRATEGIES` | Comma-separated strategy names | `momentum` |
| `TRADE_PERCENTAGE_OF_BALANCE` | % of balance per trade | `0.8` |
| `RISK_PER_TRADE` | Risk percentage per trade | `0.02` |
| `MAX_DRAWDOWN` | Maximum portfolio drawdown | `0.15` |
| `MAX_POSITIONS` | Maximum concurrent positions | `5` |
| `DAILY_LOSS_LIMIT` | Maximum daily loss | `0.05` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Optional |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | Optional |

### Strategy Configuration

Strategies are configured in `.env` and loaded via `Settings.trading.strategies`:

```python
# Example strategy parameters in code
strategy_config = StrategyConfig(
    name="momentum",
    params={
        "ema_fast": 12,
        "ema_slow": 26,
        "rsi_period": 14,
        "macd_signal": 9,
    },
)
```

---

## 🚀 Usage

### Running the Trading Bot

```bash
# Run the trading bot
python main.py

# Run in demo mode (paper trading)
python -c "
import os
os.environ['DEMO_MODE'] = 'true'
import main
"
```

### Running Backtests

```python
from backtest.engine import BacktestEngine
from indicators.indicators import IndicatorEngine
import pandas as pd

# Load historical data
df = pd.read_csv("historical_data.csv")

# Create backtest engine
engine = BacktestEngine(initial_capital=10000000)

# Define strategy function
def momentum_strategy(data, index):
    # Your strategy logic here
    return "BUY"  # or "SELL" or None

# Run backtest
result = engine.run(
    df=df,
    strategy_func=momentum_strategy,
    symbol="BTCIRT",
    strategy_name="my_momentum",
)

# View results
print(result.to_dict())
```

### Running the Example

```python
from strategy.examples import MomentumStrategy

# Create and run strategy
strategy = MomentumStrategy()
signal = strategy.generate_signal("BTCIRT")

if signal:
    print(f"Signal: {signal.signal}")
    print(f"Price: {signal.price}")
    print(f"Reason: {signal.reason}")
```

---

## 📈 Strategies

### Creating a Custom Strategy

```python
from strategy.base_strategy import (
    BaseStrategy,
    Signal,
    SignalStrength,
    StrategyConfig,
    TradingSignal,
)
from indicators.indicators import IndicatorEngine

class MyCustomStrategy(BaseStrategy):
    
    def __init__(self, config=None):
        if config is None:
            config = StrategyConfig(
                name="my_strategy",
                params={"period": 14},
            )
        super().__init__(config)
        self._period = config.params.get("period", 14)
    
    def initialize(self) -> bool:
        return True
    
    def generate_signal(self, symbol: str):
        df = self.get_candles(symbol, limit=50)
        if len(df) < self._period:
            return None
        
        rsi = self.indicator_engine.sma_rsi(df, self._period)
        current_rsi = rsi.iloc[-1]
        current_price = df["close"].iloc[-1]
        
        if current_rsi < 30:
            return self._create_signal(
                symbol=symbol,
                signal=Signal.BUY,
                strength=SignalStrength.STRONG,
                price=current_price,
                reason=f"RSI oversold at {current_rsi:.1f}",
            )
        elif current_rsi > 70:
            return self._create_signal(
                symbol=symbol,
                signal=Signal.SELL,
                strength=SignalStrength.STRONG,
                price=current_price,
                reason=f"RSI overbought at {current_rsi:.1f}",
            )
        
        return None

# Register your strategy
from strategy.strategy_manager import StrategyFactory
StrategyFactory.register("my_custom", MyCustomStrategy)
```

### Available Strategies

| Strategy | Description | Indicators |
|----------|-------------|------------|
| `momentum` | Trend-following momentum | EMA, MACD, RSI |
| `mean_reversion` | Bollinger Band reversion | BB, RSI |
| `ma_crossover` | Simple MA crossover | SMA |

---

## 🛡️ Risk Management

### Risk Parameters

Configure risk settings in `.env`:

```env
RISK_PER_TRADE=0.02              # 2% risk per trade
MAX_DRAWDOWN=0.15                # 15% max drawdown
MAX_POSITIONS=5                  # Max 5 open positions
MAX_SINGLE_ASSET_EXPOSURE=0.3    # Max 30% in single asset
DAILY_LOSS_LIMIT=0.05            # 5% daily loss limit
COOLDOWN_PERIOD=300              # 5 min cooldown after loss
DEFAULT_STOP_LOSS=0.02           # 2% default stop loss
DEFAULT_TAKE_PROFIT=0.04         # 4% default take profit
```

### Position Sizing Methods

```python
from risk.risk_manager import PositionSizer

sizer = PositionSizer()

# Fixed quantity
qty = sizer.fixed_quantity(balance=10000000, price=50000, risk_percent=0.02)

# Kelly Criterion
kelly_qty = sizer.Kelly_criterion(win_rate=0.55, avg_win=1000, avg_loss=800)

# ATR-based sizing
atr_qty = sizer.ATR_based(balance=10000000, price=50000, atr=1500, risk_percent=0.02)

# Volatility-adjusted sizing
vol_qty = sizer.volatility_adjusted(balance=10000000, price=50000, volatility=0.03)
```

---

## 📊 Backtesting

### Running a Backtest

```python
import pandas as pd
from backtest.engine import BacktestEngine

# Load your OHLCV data
df = pd.read_csv("btcirt_1h.csv")

# Create backtest engine
engine = BacktestEngine(initial_capital=10000000)

# Define strategy function
def simple_ma_strategy(data, index):
    if index < 50:
        return None
    
    sma_fast = data.iloc[:index]["close"].rolling(20).mean().iloc[-1]
    sma_slow = data.iloc[:index]["close"].rolling(50).mean().iloc[-1]
    
    if sma_fast > sma_slow:
        return "BUY"
    elif sma_fast < sma_slow:
        return "SELL"
    return None

# Run backtest
result = engine.run(
    df=df,
    strategy_func=simple_ma_strategy,
    symbol="BTCIRT",
    strategy_name="simple_ma",
    commission_rate=0.0015,
)

# Print results
print(f"Total Return: {result.total_return_percent:.2f}%")
print(f"Max Drawdown: {result.max_drawdown_percent:.2f}%")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Win Rate: {result.win_rate:.2%}")
print(f"Total Trades: {result.total_trades}")
print(f"Profit Factor: {result.profit_factor:.2f}")

# View individual trades
for trade in result.trades[:5]:
    print(f"  {trade.entry_price} -> {trade.exit_price} (PnL: {trade.pnl:,.0f})")
```

### Backtest Metrics

| Metric | Description |
|--------|-------------|
| `total_return_percent` | Total return percentage |
| `max_drawdown_percent` | Maximum drawdown |
| `sharpe_ratio` | Risk-adjusted return |
| `win_rate` | Percentage of winning trades |
| `profit_factor` | Gross profit / gross loss |
| `avg_win` | Average winning trade PnL |
| `avg_loss` | Average losing trade PnL |

---

## 📖 API Reference

### Settings

```python
from app.config import get_settings

settings = get_settings()
print(settings.nobitex.api_key)
print(settings.trading.symbols)
print(settings.risk.max_drawdown)
```

### Market Data

```python
from data.market_data import MarketDataService

service = MarketDataService()
await service.start(["BTCIRT", "ETHIRT"])

# Get candles
df = service.get_candles("BTCIRT", limit=100)
print(df.head())

# Get current price
price = service.get_price("BTCIRT")
```

### Indicators

```python
from indicators.indicators import IndicatorEngine
import pandas as pd

engine = IndicatorEngine(df)

# Moving averages
ema_12 = engine.ema(df, 12)
sma_20 = engine.sma(df, 20)

# RSI
rsi = engine.sma_rsi(df, 14)

# MACD
macd = engine.macd(df, 12, 26, 9)

# Bollinger Bands
bb = engine.bollinger_bands(df, 20, 2)

# ATR
atr = engine.atr(df, 14)
```

### Strategy Manager

```python
from strategy.strategy_manager import StrategyFactory

# Register a strategy
StrategyFactory.register("my_strategy", MyStrategy)

# Get strategy instance
strategy = StrategyFactory.create("my_strategy")

# Get all registered strategies
strategies = StrategyFactory.get_all_strategies()
```

---

## 💡 Examples

### Example 1: Simple RSI Strategy

```python
from strategy.base_strategy import BaseStrategy, Signal, SignalStrength, StrategyConfig, TradingSignal
from indicators.indicators import IndicatorEngine

class RsiStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(StrategyConfig(name="rsi", params={"rsi_period": 14}))
        self._rsi_period = 14
    
    def initialize(self):
        return True
    
    def generate_signal(self, symbol):
        df = self.get_candles(symbol, limit=50)
        rsi = self.indicator_engine.sma_rsi(df, self._rsi_period)
        
        if rsi.iloc[-1] < 30:
            return self._create_signal(
                symbol=symbol,
                signal=Signal.BUY,
                strength=SignalStrength.STRONG,
                price=df["close"].iloc[-1],
                reason="RSI oversold",
            )
        elif rsi.iloc[-1] > 70:
            return self._create_signal(
                symbol=symbol,
                signal=Signal.SELL,
                strength=SignalStrength.STRONG,
                price=df["close"].iloc[-1],
                reason="RSI overbought",
            )
        return None

# Use it
strategy = RsiStrategy()
signal = strategy.generate_signal("BTCIRT")
```

### Example 2: Complete Backtest

```python
import pandas as pd
from backtest.engine import BacktestEngine

# Load data
df = pd.read_csv("data.csv")

# Run backtest
engine = BacktestEngine()
result = engine.run(df, lambda d, i: "BUY" if d.iloc[i]["close"] > d.iloc[:i]["close"].rolling(20).mean().iloc[-1] else "SELL", "BTCIRT", "test_strategy")

# Print summary
for key, value in result.to_dict().items():
    if key != "trades":
        print(f"{key}: {value}")
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=nobitex_trader --cov-report=html

# Run specific test
python -m pytest tests/test_indicators.py -v
```

---

## 🔧 Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure you're running from the project root
cd nobitex-quant-trader
python main.py
```

**API connection issues:**
- Verify API keys in `.env`
- Check internet connection
- Verify API key permissions on Nobitex

**Strategy not generating signals:**
- Check candle data is available: `market_data.get_candles()`
- Verify indicator calculations aren't returning NaN
- Review strategy log files

**Risk manager rejecting trades:**
- Check risk summary: `risk_manager.get_risk_summary()`
- Verify daily loss limit hasn't been reached
- Check cooldown period

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all public methods
- Add tests for new features

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Nobitex Exchange for API access
- Python technical analysis libraries
- The quantitative trading community

---

## 📞 Support

For questions and support:
- Open an issue on GitHub
- Check the documentation
- Review example strategies in `strategy/examples.py`

---

<div align="center">

**Happy Trading! 📈**

</div>
=======
# tadex
>>>>>>> 5c15b18c3ca2634aa9b88587698eb1dfdd45f91d
