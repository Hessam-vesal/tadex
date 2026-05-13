
from flask import Flask, request, jsonify
from api.market import handle_market_data_route, handle_ticker_route, handle_order_book_route, handle_trades_route, close_nobitex_client
import logging
import asyncio
from flask_limiter import Limiter, rate_limit
from flask_limiter.util import get_remote_address
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Flask-Limiter Configuration
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=os.environ.get("DEFAULT_LIMITS", "100 per minute"), # Use env var or default
    storage_uri=os.environ.get("STORAGE_URI", "memory://"), # Use env var or default
)

# JWT Configuration
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "super-secret-change-me")  # Get secret key from env or use default
jwt = JWTManager(app)

logging.basicConfig(level=logging.INFO)

# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(error):
    # Log the error for debugging, but return a user-friendly JSON response
    logging.warning(f"Bad Request: {error.description}")
    return jsonify({"error": "Bad Request", "message": str(error.description)}), 400

@app.errorhandler(401)
def unauthorized(error):
    logging.warning(f"Unauthorized: {error.description}")
    return jsonify({"error": "Unauthorized", "message": "Invalid credentials or missing token."}), 401

@app.errorhandler(404)
def not_found(error):
    logging.warning(f"Not Found: {error.description}")
    return jsonify({"error": "Not Found", "message": "The requested resource was not found."}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    logging.warning(f"Method Not Allowed: {error.description}")
    return jsonify({"error": "Method Not Allowed", "message": "The HTTP method used is not allowed for this resource."}), 405

@app.errorhandler(500)
def internal_server_error(error):
    # Log the full traceback for internal server errors
    logging.exception("Internal Server Error")
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}), 500

# --- Routes ---
@app.route('/')
def home():
    return "Nobitex Quant Trader API is running!"

# Dummy login route to generate tokens
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    # In a real app, you would verify username and password against a database
    if username != "testuser" or password != "testpass":
        # Use unauthorized handler for consistency, though explicit return is also fine
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route('/chat', methods=['POST'])
@limiter.limit("5 per minute") # Example: Limit chat endpoint specifically
async def chat(): # Making chat endpoint async
    # Placeholder for chat functionality
    logging.info("Chat endpoint called")
    try:
        # Existing placeholder logic
        return jsonify({"message": "Chat functionality is under development. Please check back later."})
    except Exception as e:
        logging.exception("Error in chat endpoint")
        return jsonify({"error": "Internal Server Error", "message": "An error occurred while processing your chat request."}), 500

@app.route('/market', methods=['GET'])
@jwt_required()
async def market_data_route():
    current_user = get_jwt_identity()
    logging.info(f"Market data requested by user: {current_user}")
    symbol = request.args.get('symbol')
    interval = request.args.get('interval', '1h')
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        data = await handle_market_data_route(symbol=symbol, interval=interval)
        return jsonify(data)
    except Exception as e:
        # Log the specific error that occurred
        logging.error(f"API Route Error: Failed to fetch market data for {symbol} by user {current_user}: {e}")
        # The handle_market_data_route already returns a 500, but we can ensure it here if needed
        # For now, rely on the internal handler's return
        return jsonify({"error": f"Failed to fetch market data. Details: {str(e)}"}), 500

@app.route('/ticker', methods=['GET'])
async def ticker_route():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    try:
        data = await get_ticker_data_internal(symbol=symbol)
        return jsonify(data)
    except Exception as e:
        logging.error(f"API Route Error: Failed to fetch ticker data for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch ticker data. Details: {str(e)}"}), 500

@app.route('/order_book', methods=['GET'])
async def order_book_route():
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 10))
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

@app.route('/trades', methods=['GET'])
async def trades_route():
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 100))
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

if __name__ == '__main__':
    # To run this with async support, you would typically use an ASGI server like hypercorn or uvicorn
    # Example: hypercorn api.main:app --bind 0.0.0.0:5000 --workers 4
    # For simple testing, Flask's development server might work for basic async routes but it's not recommended for production.
    # Running with Flask dev server for now, but remember to use ASGI for proper async handling.
    app.run(host='0.0.0.0', port=5000, debug=False)
