# File: backtest_simulator.py (Upgraded with live trade simulation)

print("[DEBUG] Loaded backtest_simulator.py")

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kraken_api import KrakenClient
from ai_model import calculate_confidence
from config import Config
import matplotlib.pyplot as plt
from utils.data_loader import load_ohlcv_csv


kraken = KrakenClient()
config = Config()

STOP_LOSS = config.get("strategy.stop_loss_pct", default=0.02)
TAKE_PROFIT = config.get("strategy.take_profit_pct", default=0.05)
BULL_THRESHOLD = config.get("strategy.bull_threshold", default=0.6)

def fetch_ohlc(pair, interval=60, days=90):
    try:
        df = load_ohlcv_csv(pair)
        cutoff = (pd.Timestamp.utcnow() - pd.Timedelta(days=days)).replace(tzinfo=None)
        return df[df.index >= cutoff]
    except Exception as e:
        print(f"[OHLC] Failed to load for {pair}: {e}")
        return pd.DataFrame()



def simulate_trades(pair, df):
    balance = 1000.0
    positions = []
    trades = []

    for i in range(30, len(df)):
        window = df.iloc[i - 30:i].copy()
        current = df.iloc[i]
        price = current['close']
        score = calculate_confidence(pair)

        if positions:
            entry = positions[-1]
            entry_price = entry['price']
            change = (price - entry_price) / entry_price
            if change >= TAKE_PROFIT or change <= -STOP_LOSS or score < BULL_THRESHOLD:
                pnl = (price - entry_price) * entry['volume']
                balance += pnl
                trades.append({"buy": entry_price, "sell": price, "pnl": pnl, "score": score})
                positions.pop()

        if not positions and score >= BULL_THRESHOLD:
            volume = balance * 0.1 / price
            positions.append({"price": price, "volume": volume})
            balance -= volume * price

    return trades, balance


def plot_trades(trades):
    if not trades:
        print("[BACKTEST] No trades executed.")
        return

    cum_pnl = np.cumsum([t['pnl'] for t in trades])
    plt.plot(cum_pnl, label="Cumulative P&L")
    plt.title("Trade Backtest Result")
    plt.xlabel("Trade Index")
    plt.ylabel("Cumulative Profit (GBP)")
    plt.grid()
    plt.legend()
    plt.tight_layout()
    plt.savefig("logs/backtest_pnl.png")
    print("[BACKTEST] P&L graph saved to logs/backtest_pnl.png")

def run_backtest(pair):
    df = fetch_ohlc(pair)
    if df.empty:
        print(f"[BACKTEST] No OHLC data for {pair}")
        return None

    score = calculate_confidence(pair)
    print(f"[BACKTEST] AI score for {pair}: {score:.2f}")
    return pair, score

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    args = parser.parse_args()

    print(f"⏳ Fetching OHLC for {args.pair}...")
    df = fetch_ohlc(args.pair)
    if df.empty:
        print("[BACKTEST] No OHLC data available.")
        exit(1)

    trades, final_balance = simulate_trades(args.pair, df)
    print(f"[BACKTEST] Final balance: £{final_balance:.2f} | Trades: {len(trades)}")
    plot_trades(trades)
