from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from data.nobitex_rest_client import NobitexRESTClient

from data.api_routes import router as market_router
from data.websocket_routes import router as ws_router


app = FastAPI(title="Nobitex Quant Trader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()

client = NobitexRESTClient(
    base_url=settings.nobitex.base_url,
    timeout=10
)

app.state.client = client

app.include_router(market_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"status": "running"}
