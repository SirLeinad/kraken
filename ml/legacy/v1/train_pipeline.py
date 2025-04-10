# File: train_pipeline.py

#print("[DEBUG] Loaded train_pipeline.py")

import subprocess
from database import Database
from datetime import datetime
from config import Config
from telegram_notifications import *
from train_model_from_backtest import train_model
from backtest_simulator import run_backtest
import joblib
from pathlib import Path

Path("models").mkdir(exist_ok=True)

db = Database()
config = Config()

FOCUS_PAIRS = config.get("trading_rules.focus_pairs", default=[])
LOGFILE = "logs/train_pipeline.log"

def run_backtests():
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
        db.set_state("model_last_trained", datetime.utcnow().isoformat())
        notify("📡 AI Model retrained successfully from backtest data.", key="retrain", priority="low")

def run_pipeline(conf_threshold=0.8):
    focus = FOCUS_PAIRS
    results = {}

    for pair in focus:
        print(f"[PIPELINE] Running backtest for {pair}...")
        result = run_backtest(pair)
        if isinstance(result, tuple) and result[1] >= conf_threshold:
            results[result[0]] = result[1]

    if not results:
        print("[PIPELINE] No pairs passed the threshold.")
    return results

def save_trained_model():
    print("[TRAIN] Starting model training for v1.0...")
    model = train_model()
    joblib.dump(model, "models/model_v1.0.pkl", compress=3)
    print("[SAVE] Model dumped to models/model_v1.0.pkl")

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

if __name__ == "__main__":
    import sys
    if "--train" in sys.argv:
        save_trained_model()
    elif "--pipeline" in sys.argv:
        main()
    else:
        print("Usage: python train_pipeline.py --train | --pipeline")
