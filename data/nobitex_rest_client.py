import aiohttp
import asyncio
import logging
import os
from typing import Optional, Dict, Any, List

class NobitexRESTClient:
    """
    Asynchronous REST client for Nobitex exchange API.
    Provides methods to fetch market data, order book, trades, etc.
    
    Usage:
        client = NobitexRESTClient()
        markets = await client.get_markets()
        ticker = await client.get_ticker('BTCIRT')
        orderbook = await client.get_order_book('BTCIRT', limit=20)
    
    Configuration:
        Use environment variables or .env file for:
        - NOBITEX_API_BASE_URL (default: https://apiv2.nobitex.ir)
        - timeout (default: 10 seconds)
    """

    def __init__(self,
                 base_url: Optional[str] = None,
                 timeout: int = 10):
        self.base_url = base_url or os.getenv('NOBITEX_API_BASE_URL', 'https://apiv2.nobitex.ir')
        self.timeout = timeout
        self.logger = logging.getLogger("NobitexRESTClient")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def _request(self, method: str, path: str,
                       params: Optional[Dict[str, Any]] = None,
                       json_body: Optional[Dict[str, Any]] = None,
                       retry: int = 3) -> Any:
        url = f"{self.base_url}{path}"
        await self._ensure_session()

        for attempt in range(1, retry + 1):
            try:
                async with self._session.request(method, url, params=params, json=json_body) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        result = await resp.json()
                        self.logger.debug(f"[REST SUCCESS] {method} {url} params={params} resp={result}")
                        return result
                    else:
                        self.logger.warning(
                            f"[REST FAIL({resp.status})] {method} {url} params={params} resp={text}"
                        )
                        # Retry on 429 or 5xx
                        if resp.status in (429, 500, 502, 503, 504):
                            await asyncio.sleep(1 * attempt)
                            continue
                        resp.raise_for_status()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.error(f"[REST ERROR] {method} {url} params={params} attempt={attempt} error={e}")
                await asyncio.sleep(1 * attempt)
        raise RuntimeError(f"Failed to {method} {url} after {retry} retries")

    async def get_markets(self) -> List[str]:
        """
        دریافت لیست نمادهای معتبر بازار از API

        نکته: مستندات توصیه می کنند برای گرفتن همه سفارشات از 'all' استفاده کنیم.
        اگر این روش کار نکرد، بهتر است JSON پاسخ را برای نمادها پردازش کنیم.

        Returns:
            list of market symbols as uppercase strings, e.g. ['BTCIRT', 'ETHIRT', ...]
        """
        # طبق مستندات: `/v3/orderbook/all` لیست همه کتاب‌های سفارش را می‌آورد
        path = "/v3/orderbook/all"
        data = await self._request("GET", path)
        # data ساختار ممکن است اینگونه باشد: {"BTCIRT": {...}, "ETHIRT": {...}, ...}
        if isinstance(data, dict):
            markets = [m.upper() for m in data.keys()]
            self.logger.info(f"Markets received: {markets}")
            return markets
        else:
            self.logger.warning("Unexpected data format in get_markets response")
            return []

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        دریافت اطلاعات تیکر بازار برای نماد مشخص
        
        Args:
            symbol: بازار به شکل 'BTCIRT' (case insensitive)
        
        Returns:
            دیکشنری اطلاعات تیکر بازار
        """
        src = symbol[:-3].upper()
        dst = symbol[-3:].upper()
        path = "/market/stats"
        params = {"srcCurrency": src, "dstCurrency": dst}
        return await self._request("GET", path, params=params)

    async def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        دریافت کتاب سفارش (Order Book) برای نماد مشخص

        Args:
            symbol: بازار به شکل 'BTCIRT' (case insensitive)
            limit: تعداد سفارشات مورد نظر (بیشترین احتمالا 50 یا 100)
        
        Returns:
            دیکشنری حاوی اطلاعات بید و اسک
        """
        market = symbol.lower()
        path = f"/v2/orderbook/{market}"
        data = await self._request("GET", path)
        # بسته به API ممکن است بهتر باشد limit پارامتر شود، در مستندات فعلی نیست.
        return data

    async def get_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        دریافت آخرین سفارشات انجام شده (Trades) برای نماد مشخص

        Args:
            symbol: بازار به شکل 'BTCIRT' (case insensitive)
            limit: تعداد معاملات مورد نظر (حداکثر 100)
        
        Returns:
            لیستی از معاملات انجام شده
        """
        market = symbol.lower()
        path = f"/v2/trades/{market}"
        params = {"limit": limit}
        return await self._request("GET", path, params=params)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# --- شیوه ساده استفاده ---
# import asyncio
#
# async def main():
#     client = NobitexRESTClient()
#     markets = await client.get_markets()
#     print("Markets:", markets)
#     ticker = await client.get_ticker('BTCIRT')
#     print("Ticker BTCIRT:", ticker)
#     order_book = await client.get_order_book('BTCIRT')
#     print("Order Book BTCIRT:", order_book)
#     trades = await client.get_trades('BTCIRT')
#     print("Trades BTCIRT:", trades)
#     await client.close()
#
# asyncio.run(main())
