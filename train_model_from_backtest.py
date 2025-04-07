import pandas as pd
import joblib
import time
import platform
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from utils.data_loader import load_ohlcv_csv
from feature_engineering import engineer_features_from_ohlcv
from database import Database
import xgboost as xgb

MODEL_VERSION = "v1.0"
MODEL_PATH = f"models/model_{MODEL_VERSION}.pkl"

db = Database()

def load_all_training_data():
    ohlcv_dir = Path("data/ohlcv")
    X_all, y_all = [], []
    skipped_files = []
    start = time.time()

    for file in ohlcv_dir.glob("*_1.csv"):
        try:
            pair = file.stem.split("_")[0]

            try:
                df = pd.read_csv(
                    file,
                    header=0,
                    names=["time", "open", "high", "low", "close", "volume", "count"],
                    dtype={
                        "time": "int64",
                        "open": "float64",
                        "high": "float64",
                        "low": "float64",
                        "close": "float64",
                        "volume": "float64",
                        "count": "int64"
                    },
                    on_bad_lines="skip",  # very important
                    engine="c",
                    low_memory=False
                )
            except Exception as e:
                skipped_files.append((file.name, f"CSV Load Failed: {e}"))
                continue

            if df.iloc[0]["time"] == "time":
                df = df.iloc[1:]  # drop existing header row if duplicated

            X, y = engineer_features_from_ohlcv(df)

            if not X.empty and not y.empty:
                X_all.append(X)
                y_all.append(y)
                print(f"[LOAD] {pair}: {len(X)} samples")
            else:
                print(f"[WARN] {pair}: no data or empty features")
        except Exception as e:
            skipped_files.append((file.name, str(e)))

    if skipped_files:
        print(f"[SKIP] {len(skipped_files)} files skipped due to errors.")
        with open("skipped_files.log", "w") as logf:
            for fname, err in skipped_files:
                logf.write(f"{fname} -> {err}\n")

    if not X_all:
        print(f"[LOAD] Training data load completed in {time.time() - start:.2f} seconds")
        raise ValueError("❌ No valid training data loaded from ohlcv folder.")

    print(f"[LOAD] Training data load completed in {time.time() - start:.2f} seconds")
    return pd.concat(X_all, ignore_index=True), pd.concat(y_all, ignore_index=True)

def train_model():
    print(f"[TRAIN] Starting model training for {MODEL_VERSION}...")

    X, y = load_all_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("[INFO] Attempting to use GPU XGBoost...")
    try:
        model = xgb.XGBClassifier(
            tree_method="hist",
            device="cuda",
            n_estimators=100,
            random_state=42,
            verbosity=2
        )
        model.fit(X_train[:200], y_train[:200])  # quick dummy run to trigger GPU
        print("[GPU] XGBoost using GPU.")
    except Exception as gpu_err:
        print(f"[GPU FALLBACK] GPU failed: {gpu_err}")
        print("[CPU] Using CPU fallback.")
        model = xgb.XGBClassifier(
            tree_method="hist",
            device="cpu",
            n_estimators=100,
            random_state=42
        )

    model.fit(X_train, y_train)
    print("[INFO] Model training completed.")
    score = model.score(X_test, y_test)

    print("[SAVE] Dumping model...")
    start = time.time()

    try:
        dump(model, "models/model_v1.0.pkl", compress=3)  # optional compression
        print(f"[SAVE] Model dumped in {time.time() - start:.2f}s")
    except Exception as e:
        print(f"[ERROR] Failed to dump model: {e}")


    # DB metadata
    db.set_state("model_version", MODEL_VERSION)
    db.set_state("model_accuracy", round(score, 4))
    db.set_state("model_trained_at", datetime.utcnow().isoformat())

    # Optional: write JSON metadata too
    meta_path = Path("models/model_meta.json")
    meta_path.write_text(str({
        "version": MODEL_VERSION,
        "trained_at": datetime.utcnow().isoformat(),
        "accuracy": round(score, 4),
        "samples": len(X)
    }))

    return model


if __name__ == "__main__":
    train_model()
