# tests/test_api.py

import pytest
from app.main import app as flask_app  # Assuming your Flask app instance is named 'app' in api/main.py
from flask import url_for

@pytest.fixture
def app():
    # Create a test client for the Flask app
    yield flask_app

@pytest.fixture
def client(app):
    # Use the test client
    return app.test_client()

@pytest.fixture
def runner(app):
    # Use the test runner for CLI commands if needed, not directly used here but good practice
    return app.test_cli_runner()

def test_home_route(client):
    """Test the home route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Nobitex Quant Trader API is running!" in response.data

def test_login_route(client):
    """Test the login route to obtain an access token."""
    response = client.post('/login', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert 'access_token' in response.json
    assert response.json['access_token'] is not None

def test_login_route_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/login', json={'username': 'wronguser', 'password': 'wrongpass'})
    assert response.status_code == 401
    assert 'msg' in response.json

# Note: The following tests for protected routes require obtaining a token first.
# For simplicity in this initial setup, we'll skip obtaining the token within each test
# and assume it could be done programmatically if needed for more complex scenarios.
# In a real test suite, you'd likely have a helper function to get a token.

def test_market_data_route_unauthorized(client):
    """Test protected /market route without a token."""
    response = client.get('/market?symbol=BTCUSDT')
    assert response.status_code == 401 # Unauthorized

# To properly test protected routes, you'd need to: 
# 1. Get a token from the /login endpoint.
# 2. Include the token in the Authorization header of subsequent requests.
# Example of how to get token and use it (not fully implemented here for brevity):
# token_response = client.post('/login', json={'username': 'testuser', 'password': 'testpass'})
# access_token = token_response.json['access_token']
# headers = {'Authorization': f'Bearer {access_token}'}
# protected_response = client.get('/market?symbol=BTCUSDT', headers=headers)

def test_ticker_route(client):
    """Test the public ticker route."""
    response = client.get('/ticker?symbol=BTCUSDT')
    assert response.status_code == 200
    # Add assertions for expected ticker data structure if known

def test_chat_route(client):
    """Test the chat route (currently placeholder)."""
    response = client.post('/chat', json={'message': 'hello'})
    assert response.status_code == 200
    assert b"Chat functionality is under development" in response.data

# Note: Testing rate limiting would require sending multiple requests in quick succession
# and checking for 429 responses, which can be complex to set up in basic unit tests.
