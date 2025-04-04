# File: reset_bot_data.py

import sqlite3
import os
import glob
from pathlib import Path
import json

DB_FILE = "botdata.db"
LOG_DIR = "logs"
DATA_DIR = "data"
DISCOVERY_FILE = Path(DATA_DIR) / "discovered_pairs.json"

def reset_database():
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM trade_log")
        c.execute("DELETE FROM sqlite_sequence")
        c.execute("DELETE FROM positions")
        conn.commit()
        conn.close()
        print("[RESET] ✅ Cleared trades and positions from DB.")
    else:
        print("⚠️ No DB file found.")

def clear_logs():
    if os.path.exists(LOG_DIR):
        files = glob.glob(f"{LOG_DIR}/*")
        for f in files:
            if f.endswith(".log") or f.endswith(".csv"):
                open(f, "w").close()
        print(f"[RESET] ✅ Cleared logs in {LOG_DIR}/")
    else:
        print("⚠️ No log directory found.")

def reset_discovery():
    if DISCOVERY_FILE.exists():
        DISCOVERY_FILE.unlink()
        print("[RESET] ✅ Removed discovered_pairs.json.")
    else:
        print("⚠️ No discovered_pairs.json found.")

if __name__ == "__main__":
    reset_database()
    clear_logs()
    reset_discovery()
