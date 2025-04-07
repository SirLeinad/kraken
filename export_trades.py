# File: export_trades.py

print("[DEBUG] Loaded export_trades.py")

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_FILE = "trades.db"
EXPORT_DIR = Path("logs")
EXPORT_DIR.mkdir(exist_ok=True)

def export_trades_to_csv():
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT pair, type, volume, price, timestamp FROM trades ORDER BY timestamp DESC"
    df = pd.read_sql(query, conn)
    conn.close()

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = EXPORT_DIR / f"trades_{date_str}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Exported trades to {filename}")

if __name__ == "__main__":
    export_trades_to_csv()
