# File: run_check.py

import json
import requests
from pathlib import Path
from config import Config
from database import Database
from kraken_api import KrakenClient

config = Config()
kraken = KrakenClient()
db = Database()

def check_config_keys():
    keys = [
        "kraken.api_key", "kraken.api_secret",
        "telegram.bot_token", "telegram.chat_id",
        "strategy.stop_loss_pct", "strategy.take_profit_pct",
        "strategy.buy_allocation_pct", "strategy.exit_below_ai_score",
        "trading_rules.focus_pairs"
    ]
    missing = [k for k in keys if config.get(k) is None]
    return missing

def check_telegram():
    token = config.get("telegram.bot_token")
    chat_id = config.get("telegram.chat_id")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": chat_id, "text": "✅ Telegram check passed!"}, timeout=10)
        return resp.ok
    except Exception:
        return False

def check_kraken():
    try:
        balance = kraken.get_balance()
        return isinstance(balance, dict) and bool(balance)
    except Exception:
        return False

def check_db():
    try:
        db.save_position("TESTPAIR", 1.23, 0.001)
        positions = db.load_positions()
        if isinstance(positions, dict):
            found = "TESTPAIR" in positions
        else:
            found = any(p["pair"] == "TESTPAIR" for p in positions)
        if not found:
            print("[DB FAIL] TESTPAIR not found after save.")
            return False
        db.remove_position("TESTPAIR")
        positions = db.load_positions()
        if isinstance(positions, dict):
            still_exists = "TESTPAIR" in positions
        else:
            still_exists = any(p["pair"] == "TESTPAIR" for p in positions)
        if still_exists:
            print("[DB FAIL] TESTPAIR still present after remove.")
            return False
        print("[OK] DB read/write/remove working.")
        return True
    except Exception as e:
        print(f"[DB EXCEPTION] {e}")
        return False

def check_model():
    return Path("models/model_v1.0.pkl").exists()

def check_discovery():
    path = Path("data/discovered_pairs.json")
    return path.exists() and path.stat().st_size > 0

def run_all():
    print("🔍 Running Kraken AI Bot Health Check...\n")

    missing_keys = check_config_keys()
    if missing_keys:
        print(f"❌ Missing config keys: {missing_keys}")
    else:
        print("✅ All required config keys present.")

    print("✅ Telegram OK" if check_telegram() else "❌ Telegram failed.")
    print("✅ Kraken API OK" if check_kraken() else "❌ Kraken API failed.")
    print("✅ DB Read/Write OK" if check_db() else "❌ DB failed.")
    print("✅ Model exists" if check_model() else "❌ Model missing.")
    print("✅ Discovery data exists" if check_discovery() else "❌ Discovery file missing or empty.")

if __name__ == "__main__":
    run_all()