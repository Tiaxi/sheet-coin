"""Background collector that polls CoinGecko for cryptocurrency data."""

import asyncio
import contextlib
import logging
import time

import httpx

logger = logging.getLogger(__name__)

COINGECKO_COIN_URL = (
    "https://api.coingecko.com/api/v3/coins/{coin}"
    "?localization=false&tickers=false&market_data=true"
    "&community_data=false&developer_data=false&sparkline=false"
)
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
POLLING_DELAY = 0.1


class CryptoDataCollector:
    """Periodically fetches coin and global market data from CoinGecko."""

    def __init__(self, timeout: int = 60, polling_interval: int = 45) -> None:
        """Initialize with HTTP timeout and polling interval in seconds."""
        self.data: dict = {}
        self.requested_coin_ids: list[str] = []
        self.client = httpx.AsyncClient(timeout=timeout)
        self.polling_interval = polling_interval
        self._task: asyncio.Task | None = None

    async def _fetch_coin(self, coin: str) -> None:
        url = COINGECKO_COIN_URL.format(coin=coin)
        data = await self._api_call(url)
        if data:
            self.data[coin] = data

    async def _fetch_global(self) -> None:
        data = await self._api_call(COINGECKO_GLOBAL_URL)
        if data:
            self.data["global"] = data

    async def _api_call(self, url: str) -> dict | None:
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            await asyncio.sleep(POLLING_DELAY)
        except httpx.HTTPError:
            logger.exception("API call failed: %s", url)
            return None
        else:
            return data

    async def start(self) -> None:
        """Start the background polling loop."""
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop polling and close the HTTP client."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self.client.aclose()

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._update_all()
            except Exception:
                logger.exception("Error during coin data update")
            await asyncio.sleep(self.polling_interval)

    async def _update_all(self) -> None:
        start = time.monotonic()
        logger.info("Updating coin data")
        for coin in list(self.requested_coin_ids):
            await self._fetch_coin(coin)
        await self._fetch_global()
        elapsed = time.monotonic() - start
        logger.info("Coin data update complete (%.3fs)", elapsed)

    def get_data(self, coin_ids: list[str]) -> dict:
        """Return cached data for the requested coins and update the request list."""
        self.requested_coin_ids = [c for c in coin_ids if c != "global"]
        result = {}
        for coin in self.requested_coin_ids:
            result[coin] = self.data.get(coin)
        result["global"] = self.data.get("global")
        return result
