# File: database.py

#print("[DEBUG] Loaded database.py")

import sqlite3
import time
import csv

DB_PATH = "botdata.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()

        # Existing
        c.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                pair TEXT PRIMARY KEY,
                price REAL,
                volume REAL,
                confidence REAL,
                timestamp TEXT
            )
        """)

        # NEW table for storing dynamic keys
        c.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.conn.commit()

    def set_meta(self, key: str, value: str):
        """Set or update a key in kv_store."""
        c = self.conn.cursor()
        c.execute("REPLACE INTO kv_store (key, value, updated) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, value))
        self.conn.commit()

    def get_meta(self, key: str, default=None):
        """Get a value from kv_store, or default."""
        c = self.conn.cursor()
        c.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default

    def save_position(self, pair, price, volume):
        c = self.conn.cursor()
        c.execute("REPLACE INTO positions (pair, price, volume, confidence, timestamp) VALUES (?, ?, ?, ?, ?)", (pair, price, volume, confidence, time.ctime()))
        self.conn.commit()

    def load_positions(self):
        c = self.conn.cursor()
        c.execute("SELECT pair, price, volume, confidence FROM positions")
        rows = c.fetchall()
        return {
            pair: {'price': float(price), 'volume': float(volume), 'confidence_at_entry': float(confidence)}
            for pair, price, volume, confidence in rows
        }

    def remove_position(self, pair):
        c = self.conn.cursor()
        c.execute("DELETE FROM positions WHERE pair = ?", (pair,))
        self.conn.commit()

    def set_state(self, key, value):
        c = self.conn.cursor()
        c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    def get_state(self, key):
        c = self.conn.cursor()
        c.execute("SELECT value FROM state WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else None

    def delete_state(self, key):
        c = self.conn.cursor()
        c.execute("DELETE FROM state WHERE key = ?", (key,))
        self.conn.commit()

    def get_all_trades(self):
        path = "logs/trade_log.csv"
        trades = []
        if not os.path.exists(path):
            return trades
        with open(path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Adjust columns to match your trade log
                trades.append({
                    "timestamp": row[0],
                    "pair": row[1],
                    "type": row[2],
                    "volume": float(row[3]),
                    "price": float(row[4]),
                })
        return trades

    def clear_all_positions(self):
        with self.conn:
            self.conn.execute("DELETE FROM positions")

    def cleanup_old_data(self, max_age_hours=168):
        # Placeholder for future table pruning logic
        pass

# Usage:
# db = Database()
# db.save_position("BTC/GBP", 44000.0, 0.01)
# print(db.load_positions())