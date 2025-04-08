# File: dashboard.py

#print("[DEBUG] Loaded dashboard.py")

import sqlite3
import datetime
from config import Config
from kraken_api import KrakenClient
from telegram_notifications import *

config = Config()
kraken = KrakenClient()
DB_PATH = "botdata.db"


def show_balance():
    balance = kraken.get_balance()
    print("\n📊 Balance:")
    for asset, amount in balance.items():
        print(f"  {asset}: {amount}")
    return balance

def show_open_positions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pair, price, volume, timestamp FROM positions")
    rows = c.fetchall()
    conn.close()
    print("\n📈 Open Positions:")
    for r in rows:
        print(f"  {r[0]} — {r[2]} @ £{r[1]:.2f} [{r[3]}]")
    return rows

def show_trade_history(limit=10, pair_filter=None, action_filter=None):
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
    query = "SELECT pair, action, volume, price, timestamp FROM trade_log"
    filters = []
    values = []
    if pair_filter:
        filters.append("pair = ?")
        values.append(pair_filter.upper())
    if action_filter:
        filters.append("action = ?")
        values.append(action_filter.lower())
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id DESC LIMIT ?"
    values.append(limit)

    c.execute(query, tuple(values))
    rows = c.fetchall()
    conn.close()

    print(f"\n📜 Trades ({len(rows)} results):")
    for r in rows:
        print(f"  {r[1].upper()} {r[0]} — {r[2]} @ £{r[3]:.2f} [{r[4]}]")
    return rows


def send_daily_summary():
    balance = show_balance()
    positions = show_open_positions()
    trades = show_trade_history(limit=10)

    msg = f"<b>📊 Daily Summary for {config.user}</b>\n\n"
    msg += "<b>Balance:</b>\n" + "\n".join(f"{k}: {v}" for k, v in balance.items()) + "\n\n"

    msg += "<b>Open Positions:</b>\n"
    if positions:
        for p in positions:
            msg += f"{p[0]} — {p[2]} @ £{p[1]:.2f}\n"
    else:
        msg += "None\n"

    msg += "\n<b>Recent Trades:</b>\n"
    if trades:
        for t in trades:
            msg += f"{t[1].upper()} {t[0]} — {t[2]} @ £{t[3]:.2f}\n"
    else:
        msg += "No trades yet."

    notify(msg, key="dashboard", priority="low")


def main():
    print("""
    ========== KRAKEN AI DASHBOARD ==========
    1. Show Balance
    2. Show Open Positions
    3. Show Last 10 Trades
    4. Filter Trades by Pair
    5. Filter Trades by Action (buy/sell)
    6. Send Daily Summary via Telegram
    0. Exit
    """)
    while True:
        choice = input("Select an option: ").strip()
        if choice == "1":
            show_balance()
        elif choice == "2":
            show_open_positions()
        elif choice == "3":
            show_trade_history()
        elif choice == "4":
            pair = input("Enter trading pair (e.g. BTC/GBP): ").strip()
            show_trade_history(pair_filter=pair)
        elif choice == "5":
            action = input("Enter action (buy/sell): ").strip()
            show_trade_history(action_filter=action)
        elif choice == "6":
            send_daily_summary()
        elif choice == "0":
            break
        else:
            print("Invalid choice.")

if __name__ == '__main__':
    main()