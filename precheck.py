# File: precheck.py

import os
import json
import subprocess
import sqlite3
import requests
import time
import traceback

from pathlib import Path

import torch
import talib
import krakenex

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
        k = krakenex.API(key=api_key, secret=api_secret)
        return k.query_private('Balance').get('error') == []
    except Exception:
        return False

def check_telegram(bot_token, chat_id):
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            params={"chat_id": chat_id, "text": "✅ Precheck: Telegram is working."},
            timeout=10
        )
        return resp.status_code == 200
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
            config['kraken']['api_key'], config['kraken']['api_secret']
        ),
        "Telegram Messaging": check_telegram(
            config['telegram']['bot_token'], config['telegram']['chat_id']
        ),
        "SQLite Database RW": check_sqlite()
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
