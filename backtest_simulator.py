# File: backtest_simulator.py

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kraken_api import KrakenClient
from ai_model import calculate_confidence
from config import Config
import matplotlib.pyplot as plt

kraken = KrakenClient()
config = Config()

STOP_LOSS = config.strategy['stop_loss_pct']
TAKE_PROFIT = config.strategy.get('take_profit_pct', 0.05)
BULL_THRESHOLD = config.strategy['bull_threshold']

def fetch_ohlc(pair, interval=60, days=90):
    ohlc = kraken.get_ohlc(pair, interval=interval)
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=days)
    return ohlc[ohlc['time'] >= cutoff].copy()

def simulate_trades(pair, df):
    balance = 1000.0  # starting GBP
    positions = []
    trades = []

    for i in range(30, len(df)):
        window = df.iloc[i-30:i].copy()
        current = df.iloc[i]
        price = current['close']

        score = calculate_confidence(pair)
        if positions:
            entry = positions[-1]
            change = (price - entry['price']) / entry['price']
            if change <= -STOP_LOSS:
                trades.append({'time': current['time'], 'pair': pair, 'type': 'sell', 'price': price, 'profit': balance * change})
                balance += balance * change
                positions = []
            elif change >= TAKE_PROFIT:
                trades.append({'time': current['time'], 'pair': pair, 'type': 'sell', 'price': price, 'profit': balance * change})
                balance += balance * change
                positions = []
        else:
            if score >= BULL_THRESHOLD:
                trades.append({'time': current['time'], 'pair': pair, 'type': 'buy', 'price': price})
                positions.append({'price': price, 'time': current['time']})

    return trades, balance

def run_backtest(pair):
    print(f"⏳ Fetching 90d OHLC for {pair}...")
    df = fetch_ohlc(pair)
    print(f"📊 Loaded {len(df)} candles")

    trades, final_balance = simulate_trades(pair, df)
    trade_log = pd.DataFrame(trades)
    roi = (final_balance - 1000) / 1000

    print(f"✅ Backtest complete: Final Balance £{final_balance:.2f}, ROI: {roi:.2%}, Trades: {len(trade_log)}")
    trade_log.to_csv(f"logs/backtest_{pair}_{datetime.utcnow().date()}.csv", index=False)

    if not trade_log.empty:
        trade_log['time'] = pd.to_datetime(trade_log['time'])
        buy_prices = trade_log[trade_log['type'] == 'buy']['price'].values
        sell_prices = trade_log[trade_log['type'] == 'sell']['price'].values
        plt.plot(df['time'], df['close'], label='Price')
        for buy in buy_prices:
            plt.axhline(buy, color='green', linestyle='--', alpha=0.3)
        for sell in sell_prices:
            plt.axhline(sell, color='red', linestyle='--', alpha=0.3)
        plt.title(f"{pair} Price with Trades")
        plt.legend()
        plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True, help="Kraken trading pair like XBTGBP")
    args = parser.parse_args()
    run_backtest(args.pair)
