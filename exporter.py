# File: exporter.py

import csv
import json
import sqlite3
from pathlib import Path
import time

DB_PATH = "botdata.db"
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

def log_trade(pair, action, volume, price):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT,
            action TEXT,
            volume REAL,
            price REAL,
            timestamp TEXT
        )
    """)
    c.execute(
        "INSERT INTO trade_log (pair, action, volume, price, timestamp) VALUES (?, ?, ?, ?, ?)",
        (pair, action, volume, price, time.ctime())
    )
    conn.commit()
    conn.close()

def export_positions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pair, price, volume, timestamp FROM positions")
    rows = c.fetchall()
    with open(EXPORT_DIR / "positions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "price", "volume", "timestamp"])
        writer.writerows(rows)
    with open(EXPORT_DIR / "positions.json", "w") as f:
        data = [
            {"pair": r[0], "price": r[1], "volume": r[2], "timestamp": r[3]}
            for r in rows
        ]
        json.dump(data, f, indent=2)
    conn.close()
    print("✅ Exported positions to CSV and JSON")

def export_trade_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT,
            action TEXT,
            volume REAL,
            price REAL,
            timestamp TEXT
        )
    """)
    c.execute("SELECT pair, action, volume, price, timestamp FROM trade_log")
    rows = c.fetchall()
    with open(EXPORT_DIR / "trade_log.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "action", "volume", "price", "timestamp"])
        writer.writerows(rows)
    with open(EXPORT_DIR / "trade_log.json", "w") as f:
        data = [
            {"pair": r[0], "action": r[1], "volume": r[2], "price": r[3], "timestamp": r[4]}
            for r in rows
        ]
        json.dump(data, f, indent=2)
    conn.close()
    print("✅ Exported trade history to CSV and JSON")

if __name__ == "__main__":
    export_positions()
    export_trade_history()