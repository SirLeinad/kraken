# File: train_model_from_backtest.py

import pandas as pd
import os
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from utils.data_loader import load_ohlcv_csv
import joblib
from config import Config
from notifier import notify


config = Config()
USE_BACKTEST_TRAINING = config.get("train_from_backtest", default=False)

def engineer_features_from_ohlcv(df):
    df["hour"] = df.index.hour
    df["weekday"] = df.index.weekday
    df["target"] = (df["close"].shift(-60) > df["close"]).astype(int)
    df = df.dropna()
    X = df[["close", "hour", "weekday"]]
    y = df["target"]
    return X, y

def train_model(pair: str, notify_on_success: bool = True):
    if not USE_BACKTEST_TRAINING:
        print("⚠️ Backtest training is disabled in config.json. Enable 'train_from_backtest: true' to proceed.")
        return

    try:
        df = load_ohlcv_csv("XBTGBP", timeframe="1m")  # Or loop multiple pairs
    except Exception as e:
        print(f"[TRAIN] Failed to load OHLCVT: {e}")
        return

    X, y = engineer_features_from_ohlcv(df)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)

    joblib.dump(model, f"models/{pair}_model.pkl")
    if notify_on_success:
        notify(f"{USER}: 🧠 New model trained for {pair}. Accuracy: {score:.2%}", priority="medium")

    return model

if __name__ == "__main__":
    train_model()
