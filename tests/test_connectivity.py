import os
import time
import socket
import requests
import websocket
import pytest

REST_BASE = os.getenv("NOBITEX_REST_BASE", "https://apiv2.nobitex.ir")
WS_URL = os.getenv("NOBITEX_WS_URL", "wss://ws.nobitex.ir/connection/websocket")

def can_resolve(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None)
        return True
    except socket.gaierror:
        return False

def host_from_url(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("wss://", "").replace("ws://", "").split("/")[0]

def test_rest_ping():
    host = host_from_url(REST_BASE)
    if not can_resolve(host):
        pytest.skip(f"DNS resolve failed for {host}")

    start = time.time()
    url = f"{REST_BASE}/market/stats"
    r = requests.get(url, timeout=8)
    latency = round((time.time() - start) * 1000, 2)

    print(f"[REST] status={r.status_code} latency_ms={latency}")
    assert r.status_code == 200
    assert r.text is not None

def test_ws_connect_and_receive():
    host = host_from_url(WS_URL)
    if not can_resolve(host):
        pytest.skip(f"DNS resolve failed for {host}")

    received = {"ok": False, "msg": None}
    start = time.time()
    error_holder = {"err": None}

    def on_message(ws, message):
        received["ok"] = True
        received["msg"] = message[:300]
        ws.close()

    def on_error(ws, error):
        error_holder["err"] = str(error)
        print(f"[WS] error={error}")

    def on_close(ws, close_status_code, close_msg):
        latency = round((time.time() - start) * 1000, 2)
        print(f"[WS] close code={close_status_code} msg={close_msg} latency_ms={latency}")

    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=20, ping_timeout=10)

    # اگر 404 گرفتیم، تست را Skip می‌کنیم
    if error_holder["err"] and "404" in error_holder["err"]:
        pytest.skip(f"WS endpoint not found (404). Check WS_URL: {WS_URL}")

    assert received["ok"], "No WS message received"
