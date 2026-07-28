"""FastAPI application — modular backend (Ch.5 / Ch.18 / Ch.19)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.api.middleware import RateLimitMiddleware, RequestContextMiddleware
from src.api.routers import (
    alerts,
    assets,
    collection,
    dashboard,
    events,
    features,
    health,
    integration,
    market,
    reports,
    risk,
    security,
    system,
    validation,
)
from src.config import BASE_DIR, settings
from src.db.models import init_db
from src.logging_setup import get_logger, setup_logging
from src.websocket import websocket_endpoint

setup_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    log.info("API started chapter=19 timezone={}", settings.timezone)
    yield


app = FastAPI(
    title="BTC Analyzer API",
    version=__version__,
    description=(
        "BTC Analyzer Decision Support System — versioned REST, WebSocket, and webhook integrations. "
        "Security by default: RBAC, audit trail, secure headers (Ch.19). "
        "All external clients must use published `/api/v1/` contracts."
    ),
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
app.include_router(features.router)
app.include_router(validation.router)
app.include_router(risk.router)
app.include_router(events.router)
app.include_router(dashboard.router)
app.include_router(assets.router)
app.include_router(reports.router)
app.include_router(alerts.router)
app.include_router(integration.router)
app.include_router(security.router)
app.include_router(market.router)


@app.websocket("/ws")
@app.websocket("/api/v1/ws")
@app.websocket("/ws/v1/market/{symbol}")
async def ws_route(websocket: WebSocket, symbol: str | None = None):
    await websocket_endpoint(websocket, symbol=symbol)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["info"]["x-api-spec-version"] = "1.0"
    schema["info"]["x-security-schema-version"] = "1.0"
    schema["info"]["x-compatibility-policy"] = {
        "fields_never_repurposed": True,
        "optional_fields_may_be_added": True,
        "breaking_changes_require_major_version": True,
    }
    schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
        {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        }
    )
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
