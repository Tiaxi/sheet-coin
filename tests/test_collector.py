import httpx
import respx

from sheet_coin.collector import (
    COINGECKO_COIN_URL,
    COINGECKO_GLOBAL_URL,
    CryptoDataCollector,
)


def test_get_data_returns_requested_coins():
    collector = CryptoDataCollector()
    collector.data = {
        "bitcoin": {"price": 50000},
        "ethereum": {"price": 3000},
        "global": {"market_cap": 1e12},
    }
    result = collector.get_data(["bitcoin", "ethereum"])
    assert result == {
        "bitcoin": {"price": 50000},
        "ethereum": {"price": 3000},
        "global": {"market_cap": 1e12},
    }


def test_get_data_returns_none_for_uncached_coins():
    collector = CryptoDataCollector()
    collector.data = {"global": {"market_cap": 1e12}}
    result = collector.get_data(["bitcoin"])
    assert result == {"bitcoin": None, "global": {"market_cap": 1e12}}


def test_get_data_filters_global_from_coin_ids():
    collector = CryptoDataCollector()
    collector.data = {"global": {"market_cap": 1e12}}
    collector.get_data(["bitcoin", "global"])
    assert collector.requested_coin_ids == ["bitcoin"]


def test_get_data_updates_requested_coin_ids():
    collector = CryptoDataCollector()
    collector.get_data(["bitcoin"])
    assert collector.requested_coin_ids == ["bitcoin"]
    collector.get_data(["ethereum", "solana"])
    assert collector.requested_coin_ids == ["ethereum", "solana"]


@respx.mock
async def test_fetch_coin_caches_response():
    url = COINGECKO_COIN_URL.format(coin="bitcoin")
    respx.get(url).respond(
        json={"id": "bitcoin", "market_data": {"current_price": {"usd": 50000}}},
    )
    collector = CryptoDataCollector()
    await collector._fetch_coin("bitcoin")
    assert collector.data["bitcoin"]["id"] == "bitcoin"
    await collector.client.aclose()


@respx.mock
async def test_fetch_global_caches_response():
    respx.get(COINGECKO_GLOBAL_URL).respond(
        json={"data": {"total_market_cap": {"usd": 1e12}}},
    )
    collector = CryptoDataCollector()
    await collector._fetch_global()
    assert collector.data["global"]["data"]["total_market_cap"]["usd"] == 1e12
    await collector.client.aclose()


@respx.mock
async def test_api_call_returns_none_on_http_error():
    respx.get("https://api.example.com/fail").respond(status_code=500)
    collector = CryptoDataCollector()
    result = await collector._api_call("https://api.example.com/fail")
    assert result is None
    await collector.client.aclose()


@respx.mock
async def test_api_call_returns_none_on_network_error():
    respx.get("https://api.example.com/fail").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    collector = CryptoDataCollector()
    result = await collector._api_call("https://api.example.com/fail")
    assert result is None
    await collector.client.aclose()


@respx.mock
async def test_update_all_fetches_coins_and_global():
    coin_url = COINGECKO_COIN_URL.format(coin="bitcoin")
    respx.get(coin_url).respond(json={"id": "bitcoin"})
    respx.get(COINGECKO_GLOBAL_URL).respond(json={"data": {}})
    collector = CryptoDataCollector()
    collector.requested_coin_ids = ["bitcoin"]
    await collector._update_all()
    assert "bitcoin" in collector.data
    assert "global" in collector.data
    await collector.client.aclose()


@respx.mock
async def test_start_creates_polling_task():
    respx.get(COINGECKO_GLOBAL_URL).respond(json={"data": {}})
    collector = CryptoDataCollector(polling_interval=3600)
    await collector.start()
    assert collector._task is not None
    assert not collector._task.done()
    await collector.stop()
    assert collector._task.done()
