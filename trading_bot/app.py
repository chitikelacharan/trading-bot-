"""
app.py – Flask web UI for the Binance Futures Testnet Trading Bot
Run: py -3 app.py
Open: http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.orders import place_order

load_dotenv()
setup_logging()
logger = get_logger("webapp")

app = Flask(__name__)

def get_client():
    key    = os.getenv("BINANCE_API_KEY", "").strip()
    secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not key or not secret:
        raise ValueError("API credentials not set in .env file")
    return BinanceFuturesClient(api_key=key, api_secret=secret)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/ping")
def ping():
    try:
        client = get_client()
        client.ping()
        t = client.get_server_time()
        return jsonify({"status": "ok", "server_time": t})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/account")
def account():
    try:
        client = get_client()
        info = client.get_account_info()
        assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
        return jsonify({"status": "ok", "assets": assets})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/order", methods=["POST"])
def place():
    data = request.json or {}
    try:
        client = get_client()
        result = place_order(
            client=client,
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("order_type", ""),
            quantity=data.get("quantity"),
            price=data.get("price") or None,
            stop_price=data.get("stop_price") or None,
        )
        logger.info("Web order placed: %s", result)
        return jsonify({"status": "ok", "result": result})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 422
    except BinanceClientError as e:
        return jsonify({"status": "error", "message": f"Binance [{e.code}]: {e.msg}"}), 400
    except NetworkError as e:
        return jsonify({"status": "error", "message": f"Network error: {e}"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("\n>>> Trading Bot Web UI  -->  http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
