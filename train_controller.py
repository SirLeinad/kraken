from pathlib import Path
from train_model_from_backtest import train_model
from utils.ohlcv_sync import sync_all_ohlcv
import datetime

RETRAIN_FLAG_FILE = Path("models/RETRAIN_TRIGGERED")
LOG_FILE = "logs/train_controller.log"

def log(msg):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {msg}\n")
    print(msg)

def should_train():
    if RETRAIN_FLAG_FILE.exists():
        log("[TRAIN] Manual retrain triggered via RETRAIN_TRIGGERED.")
        return True
    return False

def run():
    log("🧠 Starting unified training controller...")

    updated = sync_all_ohlcv()
    log(f"[SYNC] Updated {len(updated)} OHLC files.")

    if not should_train():
        log("[TRAIN] No training requested. Exiting.")
        return

    pairs_to_train = sorted(set([f.split("_")[0] for f in updated])) or ["XBTUSD"]

    for pair in pairs_to_train:
        try:
            log(f"[TRAIN] Training model for {pair}...")
            train_model(pair)
        except Exception as e:
            log(f"[ERROR] Failed training for {pair}: {e}")

    if RETRAIN_FLAG_FILE.exists():
        RETRAIN_FLAG_FILE.unlink()
        log("[TRAIN] RETRAIN_TRIGGERED removed after success.")

if __name__ == "__main__":
    run()
