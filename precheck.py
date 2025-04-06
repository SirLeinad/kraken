# File: precheck.py

import os
import json
import subprocess
import sqlite3
import requests
import time
import traceback

from pathlib import Path
from config import Config
from database import Database
from kraken_api import KrakenClient

import torch
import talib
import krakenex

config = Config()
kraken = KrakenClient()
db = Database()

CONFIG_PATH = "config.json"

# Load minimal required config values for check
def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def check_conda_env():
    return os.environ.get("CONDA_DEFAULT_ENV", "") != ""

def check_gpu():
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return None

def check_talib():
    try:
        _ = talib.get_functions()
        return True
    except:
        return False

def check_kraken_api(api_key, api_secret):
    try:
        balance = kraken.get_balance()
        return isinstance(balance, dict) and bool(balance)
    except Exception:
        return False

def check_config_keys():
    required = [
        "kraken.api_key", "kraken.api_secret",
        "telegram.bot_token", "telegram.chat_id",
        "strategy.stop_loss_pct", "strategy.take_profit_pct",
        "strategy.buy_allocation_pct", "strategy.exit_below_ai_score",
        "trading_rules.focus_pairs"
    ]
    for key in required:
        if config.get(key) is None:
            print(f"[FAIL] Missing config key: {key}")
            return False
    print("[OK] All required config keys")
    return True

def check_model_exists():
    model_path = Path("models/model_v1.0.pkl")
    if not model_path.exists():
        print("[FAIL] AI model file not found")
        return False
    print("[OK] AI model file found")
    return True

def check_discovered_pairs_exists():
    path = Path("data/discovered_pairs.json")
    if not path.exists() or path.stat().st_size == 0:
        print("[FAIL] Discovery file missing or empty")
        return False
    print("[OK] Discovery file found")
    return True

def check_db_rwv():
    try:
        db.save_position("TESTPAIR", 1.23, 0.001)
        positions = db.load_positions()
        if isinstance(positions, list):
            found = any(p.get("pair") == "TESTPAIR" for p in positions)
        else:
            found = "TESTPAIR" in positions
        if not found:
            print("[DB FAIL] TESTPAIR not found after save.")
            return False
        db.remove_position("TESTPAIR")
        positions = db.load_positions()
        if isinstance(positions, list):
            still_exists = any(p.get("pair") == "TESTPAIR" for p in positions)
        else:
            still_exists = "TESTPAIR" in positions
        if still_exists:
            print("[DB FAIL] TESTPAIR still present after remove.")
            return False
        print("[OK] DB read/write/remove working.")
        return True
    except Exception as e:
        print(f"[DB EXCEPTION] {e}")
        return False

def check_telegram(bot_token, chat_id):
    token = config.get("telegram.bot_token")
    chat_id = config.get("telegram.chat_id")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": chat_id, "text": "✅ Telegram check passed!"}, timeout=10)
        return resp.ok
    except Exception:
        return False

def check_sqlite():
    try:
        conn = sqlite3.connect("botdata.db")
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, ts TEXT)")
        cur.execute("INSERT INTO test_table (ts) VALUES (?)", (time.ctime(),))
        conn.commit()
        cur.execute("DROP TABLE test_table")
        conn.close()
        return True
    except:
        return False

def run_precheck():
    print("Running environment precheck...\n")

    config = load_config()

    results = {
        "Conda Environment": check_conda_env(),
        "CUDA GPU Available": check_gpu() or "CPU fallback",
        "TA-Lib Installed": check_talib(),
        "Kraken API Access": check_kraken_api(
            config.get("kraken.api_key"), config.get("kraken.api_secret")
        ),
        "Telegram Messaging": check_telegram(
            config.get("telegram.bot_token"), config.get("telegram.chat_id")
        ),
        "SQLite Database RW": check_sqlite(),
        "Config Keys": check_config_keys(),
        "Check Model": check_model_exists(),
        "Check Discovery": check_discovered_pairs_exists(),
        "Check DB RWV": check_db_rwv()
    }

    for k, v in results.items():
        status = "✅ OK" if v else "❌ FAIL"
        print(f"{k:25}: {v if isinstance(v, str) else status}")

    failed = [k for k, v in results.items() if v is False]
    if failed:
        print("\n❌ Issues found in:", ", ".join(failed))
        print("Please resolve the issues above before proceeding.")
    else:
        print("\n✅ All checks passed. Environment is ready.")

if __name__ == '__main__':
    try:
        run_precheck()
    except Exception as e:
        print("❌ Precheck script failed with error:", str(e))
        traceback.print_exc()
