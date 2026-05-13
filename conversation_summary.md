# Conversation Summary - Nobitex Quant Trader API Documentation

## 1. Previous Conversation
The user provided the complete API documentation file (nobitex_help.txt) from the Nobitex cryptocurrency exchange platform. This is a comprehensive documentation file containing:

- Authentication and token management
- API Key management (experimental feature)
- Market data APIs (orderbook, trades, market stats, OHLC)
- User account APIs (profile, wallets, balances, transactions)
- Trading APIs (spot market orders, margin/conditional trades)
- Withdrawal APIs (crypto and fiat)
- WebSocket documentation for real-time data
- Address book and security features
- Referral program APIs
- Login/token retrieval methods

## 2. Current Work
The task was to create a detailed summary of the conversation to compact the context window while retaining key information. The nobitex_help.txt file (approximately 3000+ lines) was attached containing complete API documentation for the Nobitex exchange.

## 3. Key Technical Concepts
- **Authentication**: Token-based (Authorization: Token yourTOKENhereHEX)
- **API Key System**: Ed25519 signature-based authentication with Nobit-Key, Nobit-Signature, Nobit-Timestamp headers
- **Market Data**: Orderbook (v3), Trades (v2), Market Stats, OHLC candles
- **Trading**: Spot market orders, Market/Limit/Stop-Market/Stop-Limit executions, OCO orders
- **Margin Trading**: Conditional/delegated trading with leverage (1x-5x)
- **WebSocket**: Centrifugo-based real-time streaming at wss://ws.nobitex.ir/connection/websocket
- **Rate Limiting**: Per-API limits (e.g., 300 requests/minute for orderbook, 60/minute for trades)
- **Data Formats**: monetary values as strings, Unix timestamp for time fields
- **Supported Markets**: 150+ trading pairs including BTCIRT, ETHIRT, BTCUSDT, ETHUSDT, etc.

## 4. Relevant Files and Code
- **@nobitex_help.txt**: The main API documentation file (3000+ lines) containing all endpoint specifications
- **Project Structure**: Python-based quant trader with modules for:
  - `data/`: Market data fetching, API client, WebSocket client
  - `strategy/`: Strategy base class and management
  - `execution/`: Order execution engine
  - `risk/`: Risk management
  - `backtest/`: Backtesting engine
  - `api/`: API server for bot management
  - `indicators/`: Technical indicators
  - `portfolio/`: Portfolio management
  - `notification/`: Alert system

## 5. Problem Solving
No specific problems were solved in this conversation segment. The primary activity was receiving and processing the API documentation file.

## 6. Pending Tasks and Next Steps
- The conversation summary creation was the immediate task
- Potential next steps based on project structure:
  - Implement trading strategies using the data modules
  - Connect to Nobitex API for real-time market data
  - Set up backtesting with historical data
  - Configure risk management parameters
  - Deploy the bot for automated trading

## 7. API Endpoints Summary

### Public (No Auth Required)
- GET /v3/orderbook/{SYMBOL} - Orderbook data
- GET /v2/trades/{SYMBOL} - Recent trades
- GET /market/stats - Market statistics

### Private (Token Required)
- GET /users/profile - User profile
- GET /users/wallets/list - Wallet list
- POST /market/orders/add - Place order
- GET /market/orders/list - Order list
- GET /market/trades/list - Trade history

### Private (API Key Required)
- POST /apikeys/create - Create API key
- GET /apikeys/list - List API keys
- POST /apikeys/delete/ - Delete API key
- POST /apikeys/update/ - Update API key

### WebSocket
- Connection: wss://ws.nobitex.ir/connection/websocket
- Channels: public:orderbook-*, public:trades-*, private:orders#{param}, private:trades#{param}