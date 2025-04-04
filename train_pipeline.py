# File: train_pipeline.py

import subprocess
from datetime import datetime
from config import Config
from telegram_notifications import *
from train_model_from_backtest import train_model

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
    from backtest_pipeline import run_backtest  # adjust as needed
    results = run_backtest()  # this must return list of (pair, score)

    tradeables = {
        pair: score for pair, score in results
        if score >= conf_threshold
    }

    print(f"[PIPELINE] Selected pairs: {tradeables}")
    return tradeables
