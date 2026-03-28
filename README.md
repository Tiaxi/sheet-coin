# sheet-coin

A lightweight self-hosted proxy between the [CoinGecko API](https://www.coingecko.com/en/api) and Google Sheets. Google Apps Script polling CoinGecko directly gets heavily rate-limited due to shared Google IPs — this proxy runs on your own server, fetches coin data on a background loop, and serves cached results to your spreadsheet on demand.

Built with Python 3.14, FastAPI, httpx, and uv.

## How It Works

1. The proxy polls CoinGecko every 45 seconds (configurable) and caches coin + global market data in memory.
2. Your Google Apps Script sends a POST with a list of coin IDs and gets back the cached data instantly.
3. A generic proxy endpoint lets the script fetch any HTTPS URL through your server if needed.

Both endpoints are protected with HTTP Basic authentication.

## Quick Start

```bash
cp .env.example .env   # edit with your credentials
```

### Docker Compose (recommended)

```bash
docker compose up -d
```

### Local

```bash
uv sync
uv run sheet-coin
```

### systemd

```bash
sudo ./install.sh
```

Installs to `/opt/sheet-coin`, sets up a systemd service that runs the app via Docker Compose, and creates a `.env` from the template if one doesn't exist. Re-running updates the installation in place. Requires Docker.

## Configuration

All settings are loaded from environment variables (prefix `SHEET_COIN_`) or a `.env` file.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SHEET_COIN_AUTH_USERNAME` | Yes | — | HTTP Basic auth username |
| `SHEET_COIN_AUTH_PASSWORD` | Yes | — | HTTP Basic auth password |
| `SHEET_COIN_PORT` | No | `19877` | Server port |
| `SHEET_COIN_POLLING_INTERVAL` | No | `45` | Seconds between CoinGecko polls |
| `SHEET_COIN_API_TIMEOUT` | No | `60` | HTTP timeout for API calls |
| `SHEET_COIN_LOG_LEVEL` | No | `INFO` | Logging level |

## API

### `POST /coins`

Returns cached coin data. Send a JSON array of [CoinGecko coin IDs](https://docs.coingecko.com/reference/coins-list):

```bash
curl -u user:pass -X POST -H 'Content-Type: application/json' \
  -d '["bitcoin", "ethereum"]' \
  http://localhost:19877/coins
```

Response includes data for each requested coin plus a `global` key with market-wide data. The first request for a given coin returns `null` until the next polling cycle fetches it.

### `POST /proxy`

Proxies a GET request to an arbitrary HTTP(S) URL:

```bash
curl -u user:pass -X POST -H 'Content-Type: application/json' \
  -d '{"url": "https://api.coingecko.com/api/v3/ping"}' \
  http://localhost:19877/proxy
```

## Development

```bash
uv sync
uv run pytest -v
```

Requires Python >= 3.13.
