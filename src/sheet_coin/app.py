"""FastAPI application exposing CoinGecko data to Google Sheets."""

import logging
import secrets
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .collector import CryptoDataCollector
from .config import Settings, get_settings

logger = logging.getLogger(__name__)
security = HTTPBasic()
router = APIRouter()


def verify_credentials(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Raise 401 if Basic Auth credentials don't match settings."""
    if not (
        secrets.compare_digest(credentials.username, settings.auth_username)
        and secrets.compare_digest(credentials.password, settings.auth_password)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_collector(request: Request) -> CryptoDataCollector:
    """Extract the collector from application state."""
    return request.app.state.collector


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}


@router.post("/coins", dependencies=[Depends(verify_credentials)])
async def get_coin_data(
    request: Request,
    collector: Annotated[CryptoDataCollector, Depends(get_collector)],
) -> dict:
    """Return cached coin data for the requested IDs."""
    body = await request.json()
    return collector.get_data(body)


@router.post("/proxy", dependencies=[Depends(verify_credentials)], response_model=None)
async def proxy_request(request: Request) -> dict | Response:
    """Forward a GET request to an arbitrary URL and return the JSON response."""
    body = await request.json()
    if "url" not in body:
        return Response(status_code=204)
    parsed = urlparse(body["url"])
    if parsed.scheme not in ("https", "http"):
        raise HTTPException(status_code=400, detail="Only HTTP(S) URLs are allowed")
    logger.info("Proxy request for %s", body["url"])
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(body["url"])
        resp.raise_for_status()
    except (httpx.HTTPError, ValueError) as err:
        logger.exception("Proxy request failed: %s", body["url"])
        raise HTTPException(status_code=502, detail="Upstream request failed") from err
    else:
        return resp.json()


def create_app(
    settings: Settings | None = None,
    collector: CryptoDataCollector | None = None,
) -> FastAPI:
    """Build and return the FastAPI application."""
    _settings = settings or get_settings()
    _managed = collector is None

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        c = collector or CryptoDataCollector(
            timeout=_settings.api_timeout,
            polling_interval=_settings.polling_interval,
        )
        _app.state.collector = c
        if _managed:
            await c.start()
        yield
        if _managed:
            await c.stop()

    application = FastAPI(lifespan=lifespan)
    application.dependency_overrides[get_settings] = lambda: _settings
    if collector is not None:
        application.dependency_overrides[get_collector] = lambda: collector
    application.include_router(router)
    return application


def main() -> None:
    """Run the application with uvicorn."""
    import uvicorn  # noqa: PLC0415

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    uvicorn.run(
        "sheet_coin.app:create_app",
        host="0.0.0.0",  # noqa: S104
        port=settings.port,
        factory=True,
    )
