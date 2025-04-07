from pathlib import Path
from train_model_from_backtest import train_model
from utils.ohlcv_sync import sync_all_ohlcv
from config import Config
from database import Database
from telegram_notifications import notify
import datetime

RETRAIN_FLAG_FILE = Path("models/RETRAIN_TRIGGERED")
LOG_FILE = "logs/train_controller.log"
MAX_AGE_HOURS = 24 * 7  # 7 days
THRESHOLD_DAYS = config.get("model_staleness_days", 7)

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

def model_too_old():
    ts = db.get_state("model_last_trained")
    if not ts:
        return True
    last = datetime.datetime.fromisoformat(ts)
    age = (datetime.datetime.utcnow() - last).total_seconds() / 3600
    return age > MAX_AGE_HOURS

def run():
    log("🧠 Starting unified training controller...")

    updated = sync_all_ohlcv()
    log(f"[SYNC] Updated {len(updated)} OHLC files.")

    if not should_train():
        log("[TRAIN] No training requested. Exiting.")
        check_model_staleness()
        log("[TRAIN] Staleness check completed.")
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

def check_model_staleness():
    db = Database()
    config = Config()
    threshold_days = config.get("model_staleness_days", 7)
    ts = db.get_state("model_last_trained")

    if not ts:
        notify("⚠️ No model training timestamp found. Triggering retrain.", key="model_check", priority="high")
        Path("models/RETRAIN_TRIGGERED").touch()
        return

    last = datetime.datetime.fromisoformat(ts)
    age_days = (datetime.datetime.utcnow() - last).days

    if age_days > threshold_days:
        notify(
            f"⚠️ AI Model is {age_days} days old. Retraining has been triggered.",
            key="model_stale",
            priority="high"
        )
        Path("models/RETRAIN_TRIGGERED").touch()

if __name__ == "__main__":
    run()