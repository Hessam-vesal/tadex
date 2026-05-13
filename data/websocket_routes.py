import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{symbol}")
async def websocket_stream(websocket: WebSocket, symbol: str):

    await websocket.accept()

    try:
        while True:

            await websocket.send_json({
                "symbol": symbol,
                "status": "connected"
            })

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        print("client disconnected")
