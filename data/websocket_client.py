import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
import websockets

logger = logging.getLogger(__name__)


class NobitexRESTClient:
    """
    REST client for Nobitex public/private endpoints.
    تمرکز فعلی:
    - GET/POST عمومی و خصوصی
    - لاگ‌گیری شفاف
    - ساخت URL مطمئن
    - مدیریت timeout و خطا
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build final request URL safely.
        """
        path = path if path.startswith("/") else f"/{path}"
        url = f"{self._base_url}{path}"

        if params:
            query = urlencode(params, doseq=True)
            url = f"{url}?{query}"

        return url

    def _headers(self, authenticated: bool = False) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "nobitex-quant-trader/1.0",
        }

        if authenticated:
            if not self._token:
                raise ValueError("Token is required for authenticated requests.")
            headers["Authorization"] = f"Token {self._token}"

        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        authenticated: bool = False,
    ) -> Dict[str, Any]:
        """
        Generic HTTP request with detailed logs.
        """
        method = method.upper()
        url = self._build_url(path, params=params)
        headers = self._headers(authenticated=authenticated)

        logger.debug(
            "[REST] prepare request | method=%s | url=%s | params=%s | data=%s | auth=%s",
            method,
            url,
            params,
            data,
            authenticated,
        )

        timeout = aiohttp.ClientTimeout(total=self._timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if data else None,
                ) as response:
                    status = response.status
                    text = await response.text()

                    logger.debug(
                        "[REST] response raw | method=%s | url=%s | status=%s | body=%s",
                        method,
                        url,
                        status,
                        text[:2000],
                    )

                    try:
                        payload = json.loads(text) if text else {}
                    except json.JSONDecodeError:
                        payload = {
                            "status": "failed",
                            "code": status,
                            "message": "Non-JSON response",
                            "raw": text,
                        }

                    if status >= 400:
                        logger.warning(
                            "[REST] http error | method=%s | url=%s | status=%s | payload=%s",
                            method,
                            url,
                            status,
                            payload,
                        )
                    else:
                        logger.info(
                            "[REST] success | method=%s | url=%s | status=%s",
                            method,
                            url,
                            status,
                        )

                    return payload

        except asyncio.TimeoutError:
            logger.exception("[REST] timeout | method=%s | url=%s", method, url)
            return {
                "status": "failed",
                "message": "Request timeout",
                "url": url,
            }
        except Exception as exc:
            logger.exception("[REST] unexpected error | method=%s | url=%s", method, url)
            return {
                "status": "failed",
                "message": str(exc),
                "url": url,
            }

    async def _authenticated_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self._request(
            method=method,
            path=path,
            params=params,
            data=data,
            authenticated=True,
        )

    # ---------------------------
    # Public market endpoints
    # ---------------------------

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        دریافت اطلاعات بازار/قیمت
        توجه: endpoint دقیق ممکن است در نسخه‌های API تغییر کند.
        این ساختار طوری نوشته شده که patch کردن endpoint ساده باشد.
        """
        market = symbol.lower()
        logger.info("[REST] get_ticker | symbol=%s", market)
        return await self._request("GET", f"/market/stats", params={"srcCurrency": market[:-3], "dstCurrency": market[-3:]})

    async def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        market = symbol.lower()
        logger.info("[REST] get_order_book | symbol=%s | limit=%s", market, limit)
        return await self._request("GET", f"/v2/orderbook/{market}")

    async def get_trades(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        market = symbol.lower()
        logger.info("[REST] get_trades | symbol=%s | limit=%s", market, limit)
        return await self._request("GET", f"/trades/{market}", params={"limit": limit})

    # ---------------------------
    # Private/account examples
    # ---------------------------

    async def get_wallets(self) -> Dict[str, Any]:
        logger.info("[REST] get_wallets")
        return await self._authenticated_request("GET", "/users/wallets/list")

    async def get_orders(self, status: Optional[str] = None) -> Dict[str, Any]:
        logger.info("[REST] get_orders | status=%s", status)
        data = {}
        if status:
            data["status"] = status
        return await self._authenticated_request("POST", "/market/orders/list", data=data)


class NobitexWebSocketClient:
    """
    WebSocket client for Nobitex streams.
    تمرکز فعلی:
    - اتصال پایدار
    - subscribe/unsubscribe
    - مدیریت reconnect
    - لاگ‌گیری کامل
    """

    def __init__(
        self,
        ws_url: str,
        reconnect_delay: int = 5,
        ping_interval: int = 20,
        ping_timeout: int = 20,
    ) -> None:
        self._ws_url = ws_url
        self._reconnect_delay = reconnect_delay
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout

        self._websocket = None
        self._receiver_task: Optional[asyncio.Task] = None
        self._ws_connected = False
        self._should_run = False

        self._message_handler: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self._subscriptions: List[Dict[str, Any]] = []

    def _is_ws_open(self) -> bool:
        """
        بررسی امن باز بودن websocket
        """
        try:
            if not self._websocket or not self._ws_connected:
                return False

            if hasattr(self._websocket, "closed"):
                return not self._websocket.closed

            if hasattr(self._websocket, "state"):
                try:
                    from websockets import ConnectionState
                    return self._websocket.state == ConnectionState.OPEN
                except Exception:
                    return True

            return True
        except Exception:
            logger.exception("[WS] _is_ws_open failed")
            return False

    @property
    def is_connected(self) -> bool:
        checker = getattr(self, "_is_ws_open", None)
        if callable(checker):
            try:
                return checker()
            except Exception:
                logger.exception("[WS] is_connected checker failed")
                return False
        return False

    def set_message_handler(
        self,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._message_handler = handler
        logger.info("[WS] message handler registered")

    async def connect(self) -> bool:
        """
        Establish websocket connection.
        """
        logger.info("[WS] connecting | url=%s", self._ws_url)

        try:
            self._websocket = await websockets.connect(
                self._ws_url,
                ping_interval=self._ping_interval,
                ping_timeout=self._ping_timeout,
                close_timeout=10,
                max_size=2**20,
            )
            self._ws_connected = True
            self._should_run = True

            logger.info("[WS] connected successfully | url=%s", self._ws_url)

            self._receiver_task = asyncio.create_task(self._receiver_loop())

            if self._subscriptions:
                for sub in self._subscriptions:
                    await self.send(sub)

            return True

        except Exception as exc:
            self._ws_connected = False
            logger.exception("[WS] connect failed | url=%s | error=%s", self._ws_url, exc)
            return False

    async def disconnect(self) -> None:
        """
        Close websocket safely.
        """
        logger.info("[WS] disconnect requested")
        self._should_run = False
        self._ws_connected = False

        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("[WS] receiver task stop failed")

        if self._websocket:
            try:
                await self._websocket.close()
                logger.info("[WS] socket closed")
            except Exception:
                logger.exception("[WS] socket close failed")

        self._websocket = None

    async def send(self, payload: Dict[str, Any]) -> bool:
        """
        Send JSON payload over websocket.
        """
        if not self.is_connected:
            logger.warning("[WS] send skipped, socket is not connected | payload=%s", payload)
            return False

        try:
            raw = json.dumps(payload, ensure_ascii=False)
            await self._websocket.send(raw)
            logger.info("[WS] sent | payload=%s", raw)
            return True
        except Exception:
            logger.exception("[WS] send failed | payload=%s", payload)
            return False

    async def subscribe(self, channel: str, symbol: str) -> bool:
        """
        Subscribe to a market stream.
        ساختار payload ممکن است بسته به مستندات websocket تغییر کند.
        """
        payload = {
            "type": "subscribe",
            "channel": channel,
            "symbol": symbol,
        }

        self._subscriptions.append(payload)
        logger.info("[WS] subscribe requested | channel=%s | symbol=%s", channel, symbol)

        if self.is_connected:
            return await self.send(payload)

        logger.info("[WS] subscribe queued until connection established")
        return True

    async def unsubscribe(self, channel: str, symbol: str) -> bool:
        payload = {
            "type": "unsubscribe",
            "channel": channel,
            "symbol": symbol,
        }

        self._subscriptions = [
            sub for sub in self._subscriptions
            if not (sub.get("channel") == channel and sub.get("symbol") == symbol)
        ]

        logger.info("[WS] unsubscribe requested | channel=%s | symbol=%s", channel, symbol)

        if self.is_connected:
            return await self.send(payload)

        return True

    async def _receiver_loop(self) -> None:
        logger.info("[WS] receiver loop started")

        while self._should_run:
            if not self.is_connected:
                logger.warning("[WS] receiver detected disconnected socket")
                break

            try:
                message = await self._websocket.recv()
                logger.debug("[WS] raw message | %s", str(message)[:3000])

                try:
                    payload = json.loads(message)
                except Exception:
                    payload = {"type": "raw", "data": message}

                if self._message_handler:
                    try:
                        await self._message_handler(payload)
                    except Exception:
                        logger.exception("[WS] message handler failed | payload=%s", payload)
                else:
                    logger.info("[WS] message received | payload=%s", payload)

            except asyncio.CancelledError:
                logger.info("[WS] receiver loop cancelled")
                break
            except websockets.ConnectionClosed as exc:
                logger.warning("[WS] connection closed | code=%s | reason=%s", exc.code, exc.reason)
                self._ws_connected = False

                if self._should_run:
                    await self._reconnect()
                break
            except Exception:
                logger.exception("[WS] receiver loop error")
                self._ws_connected = False

                if self._should_run:
                    await self._reconnect()
                break

        logger.info("[WS] receiver loop finished")

    async def _reconnect(self) -> None:
        """
        Try reconnecting and restore subscriptions.
        """
        logger.warning("[WS] reconnect scheduled in %s seconds", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)

        if not self._should_run:
            logger.info("[WS] reconnect cancelled because should_run=False")
            return

        success = await self.connect()
        if success:
            logger.info("[WS] reconnect success")
        else:
            logger.error("[WS] reconnect failed")
