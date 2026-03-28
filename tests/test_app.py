import respx
from fastapi.testclient import TestClient

from sheet_coin.app import create_app
from sheet_coin.collector import CryptoDataCollector
from sheet_coin.config import Settings


def make_client():
    settings = Settings(auth_username="testuser", auth_password="testpass")
    collector = CryptoDataCollector()
    app = create_app(settings=settings, collector=collector)
    return TestClient(app), collector


def test_rejects_missing_credentials():
    client, _ = make_client()
    resp = client.post("/coins", json=["bitcoin"])
    assert resp.status_code == 401


def test_rejects_wrong_credentials():
    client, _ = make_client()
    resp = client.post("/coins", json=["bitcoin"], auth=("wrong", "creds"))
    assert resp.status_code == 401


def test_accepts_correct_credentials():
    client, _ = make_client()
    resp = client.post("/coins", json=["bitcoin"], auth=("testuser", "testpass"))
    assert resp.status_code == 200


def test_data_endpoint_returns_cached_data():
    client, collector = make_client()
    collector.data = {
        "bitcoin": {"price": 50000},
        "global": {"market_cap": 1e12},
    }
    resp = client.post("/coins", json=["bitcoin"], auth=("testuser", "testpass"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["bitcoin"] == {"price": 50000}
    assert data["global"] == {"market_cap": 1e12}


def test_data_endpoint_returns_none_for_uncached():
    client, _ = make_client()
    resp = client.post("/coins", json=["bitcoin"], auth=("testuser", "testpass"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["bitcoin"] is None
    assert data["global"] is None


def test_proxy_endpoint_forwards_request():
    client, _ = make_client()
    with respx.mock:
        respx.get("https://api.example.com/test").respond(json={"result": "ok"})
        resp = client.post(
            "/proxy",
            json={"url": "https://api.example.com/test"},
            auth=("testuser", "testpass"),
        )
    assert resp.status_code == 200
    assert resp.json() == {"result": "ok"}


def test_proxy_endpoint_returns_204_when_no_url():
    client, _ = make_client()
    resp = client.post("/proxy", json={}, auth=("testuser", "testpass"))
    assert resp.status_code == 204


def test_proxy_endpoint_rejects_invalid_scheme():
    client, _ = make_client()
    resp = client.post(
        "/proxy",
        json={"url": "file:///etc/passwd"},
        auth=("testuser", "testpass"),
    )
    assert resp.status_code == 400


def test_proxy_endpoint_returns_502_on_upstream_error():
    client, _ = make_client()
    with respx.mock:
        respx.get("https://api.example.com/fail").respond(status_code=500)
        resp = client.post(
            "/proxy",
            json={"url": "https://api.example.com/fail"},
            auth=("testuser", "testpass"),
        )
    assert resp.status_code == 502
