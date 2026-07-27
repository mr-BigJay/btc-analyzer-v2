"""FastAPI application — modular backend (Ch.5)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from src.api.routers import collection, health, market, system
from src.config import BASE_DIR, settings
from src.db.models import init_db
from src.logging_setup import get_logger, setup_logging
from src.websocket import websocket_endpoint

setup_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    log.info("API started chapter=08 timezone={}", settings.timezone)
    yield


app = FastAPI(
    title="BTC Analyzer",
    version=__version__,
    description="Market intelligence & decision support — rewrite v3 (Ch.5 backend)",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(health.router)
app.include_router(system.router)
app.include_router(collection.router)
app.include_router(market.router)


@app.websocket("/ws")
@app.websocket("/api/v1/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
