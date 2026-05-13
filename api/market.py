from data.nobitex_rest_client import NobitexRestClient
import logging
import asyncio
from flask import jsonify

nobitex_client = NobitexRestClient()

async def get_market_data_internal(symbol: str, interval: str = '1h'):
    """Internal function to fetch OHLCV data for a given symbol and interval."""
    logging.info(f"Fetching market data for symbol: {symbol}, interval: {interval}")
    try:
        # Ensure the symbol is in uppercase as expected by the client
        symbol_upper = symbol.upper()
        ohlcv_data = await nobitex_client.get_ohlcv(symbol=symbol_upper, interval=interval)
        return ohlcv_data
    except Exception as e:
        logging.error(f"Error in nobitex_client.get_ohlcv for {symbol}: {e}")
        # Re-raise the exception to be caught by the route handler
        raise

async def get_ticker_data_internal(symbol: str):
    """Internal function to fetch ticker data for a given symbol."""
    logging.info(f"Fetching ticker data for symbol: {symbol}")
    try:
        symbol_upper = symbol.upper()
        ticker_data = await nobitex_client.get_ticker(symbol=symbol_upper)
        return ticker_data
    except Exception as e:
        logging.error(f"Error in nobitex_client.get_ticker for {symbol}: {e}")
        raise

async def get_order_book_internal(symbol: str, limit: int = 10):
    """Internal function to fetch order book data for a given symbol."""
    logging.info(f"Fetching order book for symbol: {symbol} with limit: {limit}")
    try:
        symbol_upper = symbol.upper()
        order_book_data = await nobitex_client.get_order_book(symbol=symbol_upper, limit=limit)
        return order_book_data
    except Exception as e:
        logging.error(f"Error in nobitex_client.get_order_book for {symbol}: {e}")
        raise

async def get_trades_internal(symbol: str, limit: int = 100):
    """Internal function to fetch recent trades for a given symbol."""
    logging.info(f"Fetching trades for symbol: {symbol} with limit: {limit}")
    try:
        symbol_upper = symbol.upper()
        trades_data = await nobitex_client.get_trades(symbol=symbol_upper, limit=limit)
        return trades_data
    except Exception as e:
        logging.error(f"Error in nobitex_client.get_trades for {symbol}: {e}")
        raise

# --- Flask Route Handlers ---

async def handle_market_data_route(symbol: str, interval: str = '1h'):
    """Handles fetching market data (OHLCV)."""
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        data = await get_market_data_internal(symbol=symbol, interval=interval)
        return jsonify(data)
    except Exception as e:
        # Log the specific error that occurred
        logging.error(f"API Route Error: Failed to fetch market data for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch market data. Details: {str(e)}"}), 500

async def handle_ticker_route(symbol: str):
    """Handles fetching ticker data."""
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        data = await get_ticker_data_internal(symbol=symbol)
        return jsonify(data)
    except Exception as e:
        logging.error(f"API Route Error: Failed to fetch ticker data for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch ticker data. Details: {str(e)}"}), 500

async def handle_order_book_route(symbol: str, limit: int = 10):
    """Handles fetching order book data."""
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        # Ensure limit is within reasonable bounds if not already handled by client
        limit = max(1, min(limit, 100)) # Example: Limit between 1 and 100
        data = await get_order_book_internal(symbol=symbol, limit=limit)
        return jsonify(data)
    except Exception as e:
        logging.error(f"API Route Error: Failed to fetch order book for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch order book. Details: {str(e)}"}), 500

async def handle_trades_route(symbol: str, limit: int = 100):
    """Handles fetching recent trades."""
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        # Ensure limit is within reasonable bounds
        limit = max(1, min(limit, 100)) # Max limit is 100 as per client
        data = await get_trades_internal(symbol=symbol, limit=limit)
        return jsonify(data)
    except Exception as e:
        logging.error(f"API Route Error: Failed to fetch trades for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch trades. Details: {str(e)}"}), 500

# Clean up the client session when the application is shutting down
async def close_nobitex_client():
    await nobitex_client.close()
