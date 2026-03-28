import logging
import secrets
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlparse

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
):
    if not (
        secrets.compare_digest(credentials.username, settings.auth_username)
        and secrets.compare_digest(credentials.password, settings.auth_password)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_collector(request: Request) -> CryptoDataCollector:
    return request.app.state.collector


@router.post("/coins", dependencies=[Depends(verify_credentials)])
async def get_coin_data(
    request: Request,
    collector: Annotated[CryptoDataCollector, Depends(get_collector)],
):
    body = await request.json()
    return collector.get_data(body)


@router.post("/proxy", dependencies=[Depends(verify_credentials)])
async def proxy_request(request: Request):
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
        return resp.json()
    except (httpx.HTTPError, ValueError):
        logger.exception("Proxy request failed: %s", body["url"])
        raise HTTPException(status_code=502, detail="Upstream request failed")


def create_app(
    settings: Settings | None = None,
    collector: CryptoDataCollector | None = None,
) -> FastAPI:
    _settings = settings or get_settings()
    _managed = collector is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        c = collector or CryptoDataCollector(
            timeout=_settings.api_timeout,
            polling_interval=_settings.polling_interval,
        )
        app.state.collector = c
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


def main():
    import uvicorn

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    uvicorn.run(
        "sheet_coin.app:create_app",
        host="0.0.0.0",
        port=settings.port,
        factory=True,
    )
