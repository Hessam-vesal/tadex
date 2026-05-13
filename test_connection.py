import asyncio
import inspect
import logging
import os
from pprint import pprint

from dotenv import load_dotenv

from app.config import settings
from data.websocket_client import NobitexRESTClient, NobitexWebSocketClient



def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("test_connection.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logging.getLogger("websockets").setLevel(logging.DEBUG)
    logging.getLogger("aiohttp").setLevel(logging.INFO)


logger = logging.getLogger(__name__)


async def test_rest() -> None:
    logger.info("=" * 80)
    logger.info("START REST TEST")
    logger.info("=" * 80)

    rest = NobitexRESTClient(
        base_url=settings.nobitex.base_url,
        token=getattr(settings, "nobitex_token", None),
        timeout=20,
    )

    test_symbol = os.getenv("TEST_SYMBOL", "btcirt").lower()

    logger.info("[REST-TEST] base_url=%s", settings.nobitex.base_url)
    logger.info("[REST-TEST] test_symbol=%s", test_symbol)

    logger.info("[REST-TEST] ticker test started")
    ticker = await rest.get_ticker(test_symbol)
    logger.info("[REST-TEST] ticker response:")
    pprint(ticker)

    logger.info("[REST-TEST] order book test started")
    order_book = await rest.get_order_book(test_symbol, limit=3)
    logger.info("[REST-TEST] order book response:")
    pprint(order_book)

    logger.info("[REST-TEST] trades test started")
    trades = await rest.get_trades(test_symbol, limit=3)
    logger.info("[REST-TEST] trades response:")
    pprint(trades)

    logger.info("[REST-TEST] completed")


async def ws_message_handler(message):
    logger.info("[WS-HANDLER] message received")
    pprint(message)


async def test_websocket() -> None:
    logger.info("=" * 80)
    logger.info("START WEBSOCKET TEST")
    logger.info("=" * 80)

    logger.info("[WS-TEST] class file: %s", inspect.getfile(NobitexWebSocketClient))
    logger.info("[WS-TEST] has _is_ws_open: %s", hasattr(NobitexWebSocketClient, "_is_ws_open"))
    logger.info("[WS-TEST] has is_connected: %s", hasattr(NobitexWebSocketClient, "is_connected"))

    ws = NobitexWebSocketClient(
        ws_url=settings.nobitex.ws_url,
        reconnect_delay=5,
        ping_interval=20,
        ping_timeout=20,
    )

    ws.set_message_handler(ws_message_handler)

    logger.info("[WS-TEST] ws_url=%s", settings.nobitex.ws_url)

    connected = await ws.connect()
    logger.info("[WS-TEST] connect result=%s", connected)
    logger.info("[WS-TEST] is_connected=%s", ws.is_connected)

    if not connected:
        logger.error("[WS-TEST] websocket connection failed")
        return

    test_symbol = os.getenv("TEST_SYMBOL", "btcirt").lower()

    # توجه:
    # ساختار subscribe بسته به نسخه websocket نوبیتکس ممکن است تغییر کند.
    # اینجا یک تست ماژولار داریم که اگر payload نیاز به اصلاح داشت، فقط همین لایه patch می‌شود.
    await ws.subscribe(channel="trades", symbol=test_symbol)
    await ws.subscribe(channel="orderbook", symbol=test_symbol)

    logger.info("[WS-TEST] waiting 20 seconds for incoming messages...")
    await asyncio.sleep(20)

    logger.info("[WS-TEST] disconnecting")
    await ws.disconnect()
    logger.info("[WS-TEST] websocket test completed")


async def main():
    load_dotenv()
    setup_logging()

    logger.info("START CONNECTION TEST")
    logger.info("base_url=%s", settings.nobitex.base_url)
    logger.info("ws_url=%s", settings.nobitex.ws_url)


    try:
        await test_rest()
    except Exception:
        logger.exception("REST TEST FAILED")

    try:
        await test_websocket()
    except Exception:
        logger.exception("WEBSOCKET TEST FAILED")

    logger.info("ALL TESTS FINISHED")


if __name__ == "__main__":
    asyncio.run(main())
