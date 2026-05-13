"""
Security module for Nobitex Quant Trader.

Handles API key encryption, request signing, and secure credential management.
"""

import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Optional
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.logger import get_logger

logger = get_logger("nobitex_trader.security")


class APICredentials:
    """Manages API credentials securely."""

    def __init__(self, api_key: str, secret: str):
        """Initialize API credentials."""
        self._api_key = api_key
        self._secret = secret
        self._nonce = int(time.time() * 1000)

    @property
    def api_key(self) -> str:
        """Get API key."""
        return self._api_key

    @property
    def secret(self) -> str:
        """Get secret (do NOT log this!)."""
        return self._secret

    def get_nonce(self) -> int:
        """Get and increment the request nonce."""
        current_nonce = self._nonce
        self._nonce = max(self._nonce + 1, int(time.time() * 1000))
        return current_nonce

    def sign_request(self, params: Dict[str, str]) -> str:
        """
        Sign a request with the API secret.
        Nobitex uses HMAC-SHA512 signing.
        """
        params["key"] = self._api_key
        params["signature"] = self._generate_signature(params)
        return urlencode(params)

    def _generate_signature(self, params: Dict[str, str]) -> str:
        """Generate HMAC-SHA512 signature for the request."""
        query = urlencode(params)
        signature = hmac.new(
            self._secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        return signature


class CredentialManager:
    """Manages encryption and storage of credentials."""

    _instance: Optional["CredentialManager"] = None

    def __init__(self, master_password: Optional[str] = None):
        """Initialize credential manager with encryption."""
        self._fernet = self._init_encryption(master_password)
        logger.debug("Credential manager initialized")

    @classmethod
    def get_instance(cls, master_password: Optional[str] = None) -> "CredentialManager":
        """Get singleton instance of CredentialManager."""
        if cls._instance is None:
            cls._instance = cls(master_password)
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        cls._instance = None

    def _init_encryption(self, master_password: Optional[str]) -> Fernet:
        """Initialize Fernet encryption with key from password."""
        if not master_password:
            master_password = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")

        # Derive key from password
        salt = b"nobitex_quant_salt"  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        token = self._fernet.encrypt(plaintext.encode())
        return token.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt credential - invalid token")
            raise

    def store_credential(self, name: str, value: str):
        """Store a credential in environment or file."""
        encrypted = self.encrypt(value)
        env_var = f"CRED_{name.upper()}"
        os.environ[env_var] = encrypted
        logger.debug(f"Credential '{name}' stored (encrypted)")

    def get_credential(self, name: str) -> Optional[str]:
        """Retrieve a credential."""
        env_var = f"CRED_{name.upper()}"
        encrypted = os.getenv(env_var)
        if encrypted:
            try:
                return self.decrypt(encrypted)
            except Exception as e:
                logger.error(f"Failed to retrieve credential '{name}': {e}")
        return None


class RateLimiter:
    """Implements token bucket rate limiting for API requests."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self._max_requests = max_requests
        self._window = window_seconds
        self._tokens = max_requests
        self._last_refill = time.time()
        self._lock = False  # Simple lock (use threading.Lock in async context)

    def acquire(self) -> bool:
        """Try to acquire a rate limit token. Returns True if allowed."""
        now = time.time()

        # Refill tokens based on elapsed time
        elapsed = now - self._last_refill
        refill_rate = self._max_requests / self._window
        new_tokens = elapsed * refill_rate

        if new_tokens >= 1:
            self._tokens = min(self._max_requests, self._tokens + new_tokens)
            self._last_refill = now

        if self._tokens >= 1:
            self._tokens -= 1
            return True

        return False

    def wait_time(self) -> float:
        """Get the time to wait before the next request is allowed."""
        if self._tokens >= 1:
            return 0

        refill_rate = self._max_requests / self._window
        return (1 - self._tokens) / refill_rate

    @property
    def available_tokens(self) -> float:
        """Get the number of available tokens."""
        now = time.time()
        elapsed = now - self._last_refill
        refill_rate = self._max_requests / self._window
        return min(self._max_requests, self._tokens + elapsed * refill_rate)


class RequestSigner:
    """Handles HTTP request signing for Nobitex API."""

    def __init__(self, credentials: APICredentials):
        """Initialize request signer."""
        self._credentials = credentials

    def sign(self, method: str, path: str, params: Optional[Dict] = None) -> Dict:
        """
        Sign an API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Request parameters

        Returns:
            Signed request headers and params
        """
        if params is None:
            params = {}

        # Add timestamp nonce
        params["_nonce"] = str(self._credentials.get_nonce())

        # Generate signature
        signed_params = self._credentials.sign_request(params)

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self._credentials.api_key,
        }

        return {
            "method": method.upper(),
            "path": path,
            "params": params if method == "GET" else signed_params,
            "headers": headers,
        }


class SecureConfigLoader:
    """Loads configuration with secure credential handling."""

    @staticmethod
    def load_api_credentials() -> Optional[APICredentials]:
        """Load API credentials from environment variables."""
        api_key = os.getenv("NOBITEX_API_KEY", "")
        secret = os.getenv("NOBITEX_SECRET", "")

        if not api_key or not secret:
            logger.warning("API credentials not configured")
            return None

        return APICredentials(api_key, secret)

    @staticmethod
    def validate_credentials(credentials: Optional[APICredentials]) -> bool:
        """Validate that API credentials are properly configured."""
        if credentials is None:
            return False

        if not credentials.api_key or not credentials.secret:
            return False

        return True

    @staticmethod
    def check_security_setup() -> Dict[str, bool]:
        """Check if security setup is complete."""
        return {
            "api_credentials_loaded": SecureConfigLoader.validate_credentials(
                SecureConfigLoader.load_api_credentials()
            ),
            "env_file_exists": os.path.exists(".env"),
            "gitignore_exists": os.path.exists(".gitignore"),
        }
