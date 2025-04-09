# train_new_model.py

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

DATA_PATH = "data/training_dataset.csv"
MODEL_PATH = "models/model_v2.pkl"
os.makedirs("models", exist_ok=True)

def train():
    print("[INFO] Loading full dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"[INFO] Loaded {len(df)} rows")

    features = ["sma", "rsi", "price_delta", "volume_delta", "volatility"]
    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        tree_method="gpu_hist"
    )

    print("[INFO] Training XGBoost model on GPU...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, digits=4)
    print("[INFO] Classification Report:")
    print(report)

    joblib.dump(model, MODEL_PATH)
    print(f"[✅] Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()