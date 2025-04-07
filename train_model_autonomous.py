print("[DEBUG] Loaded train_model_autonomous.py")

from train_model_from_backtest import train_model
from utils.ohlcv_sync import sync_all_ohlcv

# Flag to avoid retraining unnecessarily
RETRAIN_FLAG_FILE = "models/RETRAIN_TRIGGERED"

if not Path(RETRAIN_FLAG_FILE).exists():
    print("[AUTO] No retraining requested. Skipping.")
    exit(0)

def run_autonomous_cycle():
    print("[AUTO] Syncing OHLCV files...")
    updated_pairs = sync_all_ohlcv()

    print("[AUTO] Training models...")
    for update in updated_pairs:
        pair, _ = update.split("_")
        try:
            print(f"[AUTO] Training model for {pair}...")
            train_model(pair)
        except Exception as e:
            print(f"[AUTO] Failed to train {pair}: {e}")

if __name__ == "__main__":
    run_autonomous_cycle()