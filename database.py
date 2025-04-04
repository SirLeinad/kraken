# File: database.py

import sqlite3
import time

DB_PATH = "botdata.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                pair TEXT PRIMARY KEY,
                price REAL,
                volume REAL,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def save_position(self, pair, price, volume):
        c = self.conn.cursor()
        c.execute("REPLACE INTO positions (pair, price, volume, timestamp) VALUES (?, ?, ?, ?)",
                  (pair, price, volume, time.ctime()))
        self.conn.commit()

    def load_positions(self):
        c = self.conn.cursor()
        c.execute("SELECT pair, price, volume FROM positions")
        rows = c.fetchall()
        return {pair: {'price': price, 'volume': volume} for pair, price, volume in rows}

    def remove_position(self, pair):
        c = self.conn.cursor()
        c.execute("DELETE FROM positions WHERE pair = ?", (pair,))
        self.conn.commit()

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