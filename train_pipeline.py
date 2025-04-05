# File: train_pipeline.py

import subprocess
from datetime import datetime
from config import Config
from telegram_notifications import *
from train_model_from_backtest import train_model
import joblib
joblib.dump(train_model(), "models/model_v1.0.pkl")

config = Config()

FOCUS_PAIRS = config.strategy['focus_pairs']
LOGFILE = "logs/train_pipeline.log"

def print('[PIPELINE] Running backtests...')
    run_backtests():
    with open(LOGFILE, "a") as log:
        log.write(f"\n[{datetime.utcnow().isoformat()}] Starting backtests...\n")
        for pair in FOCUS_PAIRS:
            cmd = ["python", "backtest_simulator.py", "--pair", pair]
            result = subprocess.run(cmd, capture_output=True, text=True)
            log.write(f"Backtest {pair}:\n{result.stdout}\n")

def main():
    print('[PIPELINE] Running backtests...')
    run_backtests()
    if config.get("train_from_backtest", False):
        with open(LOGFILE, "a") as log:
            log.write(f"\n[{datetime.utcnow().isoformat()}] Training model...\n")
        print('[PIPELINE] Training model from backtests...')
        train_model()
        notify("📡 AI Model retrained successfully from backtest data.", key="retrain", priority="low")

if __name__ == "__main__":
    run_pipeline()

def run_pipeline(conf_threshold=0.8):
    from backtest_pipeline import run_backtest
    raw_results = run_backtest()  # Expected: list of (pair, score)

    tradeables = {}
    for item in raw_results:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            print(f"[PIPELINE] Skipping malformed result: {item}")
            continue
        pair, score = item
        if isinstance(pair, str) and isinstance(score, (float, int)) and score >= conf_threshold:
            tradeables[pair] = score
        else:
            print(f"[PIPELINE] Invalid score or pair format: {item}")

    print(f"[PIPELINE] Selected pairs: {tradeables}")
    return tradeables

def load_trade_history_for_training():
    try:
        import json
        from pathlib import Path

        path = Path("data/trade_history.json")
        if not path.exists():
            return []

        with path.open() as f:
            trades = [json.loads(line) for line in f if line.strip()]
        return trades
    except Exception as e:
        print(f"[TRAIN] Failed to load trade history: {e}")
        return []
    # do not use in strategy, logger or telegram_bot.
    # Usage python train_pipeline.py
