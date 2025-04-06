import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from utils.data_loader import load_ohlcv_csv
from feature_engineering import engineer_features_from_ohlcv
from database import Database

MODEL_VERSION = "v1.0"
MODEL_PATH = f"models/model_{MODEL_VERSION}.pkl"

db = Database()

def load_all_training_data():
    ohlcv_dir = Path("data/ohlcv")
    X_all, y_all = [], []
    skipped_files = []

    for file in ohlcv_dir.glob("*_1.csv"):  # ONLY 1-minute interval
        try:
            pair = file.stem.split("_")[0]
            df = pd.read_csv(file)
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
        raise ValueError("❌ No valid training data loaded from ohlcv folder.")

    return pd.concat(X_all, ignore_index=True), pd.concat(y_all, ignore_index=True)

def train_model():
    print(f"[TRAIN] Starting model training for {MODEL_VERSION}...")

    X, y = load_all_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)

    # Save model file
    joblib.dump(model, MODEL_PATH)
    print(f"[SAVE] Trained model saved: {MODEL_PATH} (acc={score:.2%})")

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
