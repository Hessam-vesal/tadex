
from flask import Flask, request, jsonify
from api.market import handle_market_data_route, handle_ticker_route, handle_order_book_route, handle_trades_route, close_nobitex_client
import logging
import asyncio

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Nobitex Quant Trader API is running!"

@app.route('/chat', methods=['POST'])
async def chat(): # Making chat endpoint async
    # Placeholder for chat functionality
    logging.info("Chat endpoint called")
    return jsonify({"response": "Chat endpoint not yet implemented."})

@app.route('/market', methods=['GET'])
async def market_data_route():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval', '1h')
    return await handle_market_data_route(symbol=symbol, interval=interval)

@app.route('/ticker', methods=['GET'])
async def ticker_route():
    symbol = request.args.get('symbol')
    return await handle_ticker_route(symbol=symbol)

@app.route('/order_book', methods=['GET'])
async def order_book_route():
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 10))
    return await handle_order_book_route(symbol=symbol, limit=limit)

@app.route('/trades', methods=['GET'])
async def trades_route():
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 100))
    return await handle_trades_route(symbol=symbol, limit=limit)

# Graceful shutdown handler
import signal

def shutdown_handler(signum, frame):
    logging.info("Shutting down...")
    asyncio.create_task(close_nobitex_client())
    # In a real async Flask app with ASGI, you might need more sophisticated shutdown handling
    # For this example, we'll just log and exit
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    # To run this with async support, you would typically use an ASGI server like hypercorn or uvicorn
    # Example: hypercorn api.main:app --bind 0.0.0.0:5000 --workers 4
    # For simple testing, Flask's development server might work for basic async routes but it's not recommended for production.
    # Running with Flask dev server for now, but remember to use ASGI for proper async handling.
    app.run(host='0.0.0.0', port=5000, debug=False)
