# File: main.py

#print("[DEBUG] Loaded main.py")

import builtins
import time
import datetime
import os
import sys
import threading

print = lambda *args, **kwargs: builtins.print(*args, flush=True, **kwargs)

#print("[DEBUG] main.py starting")

from pathlib import Path
from config import Config
from database import Database
from dashboard import send_daily_summary, show_balance, show_open_positions, show_trade_history
from telegram_notifications import *

config = Config()
db = Database()
loop_interval = config.get("strategy.loop_interval_sec", default=60)
INTERVAL = config.get("discovery.interval_hours") * 3600
USER = config.get("user")
SUMMARY_TIME = config.get("summary_time", default="08:00")  # HH:MM
SUMMARY_HOUR, SUMMARY_MINUTE = map(int, SUMMARY_TIME.split(":"))
last_discovery = float(db.get_state("last_discovery") or 0)
last_summary_date = db.get_state("last_summary_date")
SUMMARY_DIR = Path("summaries")
SUMMARY_DIR.mkdir(exist_ok=True)
MAX_SUMMARY_AGE_DAYS = int(config.get("summary_retention_days", default=14))

def restart_bot():
    print("[RELOAD] Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

def archive_daily_summary():
    from export_trades import export_trades_to_csv
    export_trades_to_csv()

    dt = datetime.datetime.now()
    date_str = dt.strftime("%Y-%m-%d")
    filepath = SUMMARY_DIR / f"summary_{date_str}.txt"

    balance = show_balance()
    positions = show_open_positions()
    trades = show_trade_history(limit=5)

    with open(filepath, "w") as f:
        f.write(f"Daily Summary for {USER} - {date_str}\n\n")
        f.write("Balance:\n")
        for k, v in balance.items():
            f.write(f"  {k}: {v}\n")

        f.write("\nOpen Positions:\n")
        if positions:
            for p in positions:
                f.write(f"  {p[0]} — {p[2]} @ £{p[1]:.2f} [{p[3]}]\n")
        else:
            f.write("  None\n")

        f.write("\nRecent Trades:\n")
        if trades:
            for t in trades:
                f.write(f"  {t[1].upper()} {t[0]} — {t[2]} @ £{t[3]:.2f} [{t[4]}]\n")
        else:
            f.write("  No trades yet.\n")

    cleanup_old_summaries()

def cleanup_old_summaries():
    cutoff = datetime.datetime.now() - datetime.timedelta(days=MAX_SUMMARY_AGE_DAYS)
    for file in SUMMARY_DIR.glob("summary_*.txt"):
        try:
            date_str = file.stem.replace("summary_", "")
            file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                file.unlink()
        except Exception:
            continue

def run_bot():
    print('[INIT] Kraken AI bot starting...')
    global last_discovery, last_summary_date

    if config.get("paper_trading") is True:
        notify(f"{USER}: Kraken AI Bot started. Paper trading enabled.", key="startup", priority="high")
        print("[INFO] Paper Trading Enabled, Bot Started")
    else:
        notify(f"{USER}: Kraken AI Bot started. Live trading enabled.", key="startup", priority="high")
        print("[INFO] Live Trading Enabled, Bot Started")

    #print("[DEBUG] After notify, before strategy")
    from strategy import TradeStrategy
    strategy = TradeStrategy()
    #print("[DEBUG] Strategy object created")

    while True:
        start_time = time.time()

        try:
            print('[LOOP] Executing strategy...')
            strategy.execute()
        except Exception as e:
            print(f"[ERROR] strategy.execute failed: {e}")

        # Daily summary
        dt_now = datetime.datetime.now()
        if dt_now.strftime("%H:%M") == config.get("summary_time") and (last_summary_date != dt_now.date().isoformat()):
            try:
                strategy.send_daily_summary()
                archive_daily_summary()
                export_trades_to_csv()
                db.set_state("last_summary_date", dt_now.date().isoformat())  # <-- This updates DB
            except Exception as e:
                notify(f"{USER}: Bot error occurred: {e}", key="error", priority="medium")

        # Discovery interval
        from discovery import PairDiscovery
        discovery = PairDiscovery()
        now = time.time()
        if time.time() - last_discovery >= INTERVAL:
            try:
                PairDiscovery().get_eligible_pairs()
                db.set_state("last_discovery", time.time())  # <-- This line updates DB
            except Exception as e:
                print(f"[ERROR] Discovery failed: {e}")

        elapsed = time.time() - start_time
        delay = max(loop_interval - elapsed, 0)
        print(f"[LOOP] Sleeping for {delay:.2f} seconds...")
        time.sleep(delay)

if __name__ == '__main__':
    run_bot()