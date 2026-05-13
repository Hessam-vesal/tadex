from fastapi import APIRouter, Request, HTTPException

router = APIRouter(tags=["market"])


@router.get("/markets")
async def markets(request: Request):
    try:
        return await request.app.state.client.get_markets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{symbol}")
async def ticker(symbol: str, request: Request):
    try:
        return await request.app.state.client.get_ticker(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{symbol}")
async def orderbook(symbol: str, request: Request):
    try:
        return await request.app.state.client.get_order_book(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
