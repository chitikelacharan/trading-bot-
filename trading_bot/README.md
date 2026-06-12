# Binance Futures Testnet Trading Bot

A clean, production-quality Python trading bot for placing **Market**, **Limit**, and **Stop-Market** orders on the [Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M).

---

## ✨ Features

| Feature | Details |
|---|---|
| Order types | MARKET · LIMIT · STOP_MARKET (bonus) |
| Sides | BUY · SELL |
| Input validation | Symbol, side, type, quantity, price, stop-price |
| Logging | Rotating file log (`logs/trading_bot.log`) + console |
| Error handling | API errors, network timeouts, invalid inputs |
| CLI | `argparse` with sub-commands: `place`, `ping`, `account` |
| Security | Credentials via `.env` – never hard-coded |

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Binance REST client (HMAC signing, logging)
│   ├── orders.py            # Order placement logic & response formatting
│   ├── validators.py        # Input validation helpers
│   └── logging_config.py   # Rotating file + console logger
├── logs/                    # Auto-created; contains trading_bot.log
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt
├── .env.example             # Template – copy to .env and fill in your keys
└── README.md
```

---

## ⚙️ Setup

### 1. Get Testnet API Credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with your GitHub account.
3. Click **"Generate HMAC_SHA256 Key"**.
4. Copy the **API Key** and **Secret Key** shown on screen (the secret is shown only once).

### 2. Clone / Download the Project

```bash
git clone <your-repo-url>
cd trading_bot
```

Or unzip the folder and `cd` into `trading_bot/`.

### 3. Create & Activate a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API Credentials

```bash
# Copy the template
cp .env.example .env   # macOS / Linux
copy .env.example .env # Windows
```

Open `.env` in any text editor and fill in your testnet credentials:

```
BINANCE_API_KEY=paste_your_api_key_here
BINANCE_API_SECRET=paste_your_secret_key_here
```

> ⚠️ **Never commit `.env` to source control.**

---

## 🚀 How to Run

All commands are run from inside the `trading_bot/` directory.

### Test Connectivity

```bash
python cli.py ping
```

Expected output:
```
╔══════════════════════════════════════════════════════════════╗
║        Binance Futures Testnet Trading Bot  v1.0             ║
╚══════════════════════════════════════════════════════════════╝
  🔗  Pinging Binance Futures Testnet …
  🟢  Testnet is reachable! Server time: 1718123456789 ms
```

---

### Place a MARKET Order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

Skip the confirmation prompt with `-y`:

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 -y
```

---

### Place a LIMIT Order

```bash
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000
```

---

### Place a STOP_MARKET Order (Bonus)

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 50000
```

---

### Show Account Balances

```bash
python cli.py account
```

---

### Get Full JSON Response

Append `--json` to any command:

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 -y --json
```

---

## 📋 CLI Reference

```
usage: trading_bot [-h] {place,ping,account} ...

sub-commands:
  place    Place a MARKET, LIMIT, or STOP_MARKET order
  ping     Test connectivity to the testnet
  account  Show account balance summary

place arguments:
  --symbol / -s   SYMBOL     Trading pair (e.g. BTCUSDT)       [required]
  --side          SIDE       BUY | SELL                         [required]
  --type  / -t    TYPE       MARKET | LIMIT | STOP_MARKET       [required]
  --quantity / -q QTY        Order quantity                     [required]
  --price / -p    PRICE      Limit price (LIMIT orders)         [optional]
  --stop-price    STOP_PRICE Stop trigger price (STOP_MARKET)   [optional]
  --yes / -y                 Skip confirmation prompt           [flag]
  --json                     Print full JSON response           [flag]
```

---

## 📝 Logging

Logs are written to **`logs/trading_bot.log`** (rotating, max 5 MB × 3 files).

Console shows **INFO** and above; the file captures **DEBUG** level (full request / response bodies).

Sample log entries:

```
2026-06-12 10:30:01 | INFO     | Logging initialised → logs/trading_bot.log
2026-06-12 10:30:02 | INFO     | Ping successful – testnet is reachable.
2026-06-12 10:30:03 | INFO     | Order validated | symbol=BTCUSDT side=BUY type=MARKET qty=0.01 …
2026-06-12 10:30:03 | DEBUG    | → POST https://testnet.binancefuture.com/fapi/v1/order | params=…
2026-06-12 10:30:04 | DEBUG    | ← HTTP 200 | body={"orderId":…}
2026-06-12 10:30:04 | INFO     | Order accepted | orderId=123456 status=FILLED executedQty=0.01 …
```

---

## 🔒 Assumptions

1. Only **USDT-M** futures pairs are supported (symbols must end with `USDT`).
2. LIMIT orders use **GTC** (Good-Till-Cancelled) by default.
3. STOP_MARKET is a closing/triggering order; `closePosition` is set to `false` so a custom quantity is respected.
4. The testnet sometimes has lower liquidity; LIMIT orders may stay in `NEW` status.
5. Quantity limits are partially validated client-side; Binance enforces symbol-specific `LOT_SIZE` filters server-side.

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `requests` | ≥ 2.31.0 | HTTP REST calls to Binance API |
| `python-dotenv` | ≥ 1.0.0 | Load API keys from `.env` file |

> No Binance SDK is used – all API calls are raw REST with HMAC-SHA256 signing.

---

## 🛡️ Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API keys | Clear error message, exit 1 |
| Invalid symbol / side / type | Descriptive `ValueError`, exit 1 |
| Network timeout | `NetworkError` with timeout info |
| Binance rejects order | `BinanceClientError` with code + message |
| Keyboard interrupt | Graceful exit with message |
