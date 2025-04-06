# File: train_model_from_backtest.py

import pandas as pd
import os
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
import joblib
from config import Config

config = Config()
USE_BACKTEST_TRAINING = config.get("train_from_backtest", default=False)

def load_backtest_data(log_dir="logs"):
    all = []
    for f in os.listdir(log_dir):
        if f.startswith("backtest_") and f.endswith(".csv"):
            df = pd.read_csv(os.path.join(log_dir, f))
            if "type" in df.columns and "price" in df.columns:
                all.append(df)
    return pd.concat(all, ignore_index=True) if all else pd.DataFrame()

def engineer_features(df):
    df['hour'] = pd.to_datetime(df['time']).dt.hour
    df['weekday'] = pd.to_datetime(df['time']).dt.weekday
    df['target'] = df['type'].map({'buy': 1, 'sell': 0})
    df = df.dropna()
    features = df[['price', 'hour', 'weekday']]
    labels = df['target']
    return features, labels

def train_model():
    if not USE_BACKTEST_TRAINING:
        print("⚠️ Backtest training is disabled in config.json. Enable 'train_from_backtest: true' to proceed.")
        return

    df = load_backtest_data()
    if df.empty:
        print("No backtest trade data found.")
        return

    X, y = engineer_features(df)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    print(f"✅ Model trained on {len(df)} entries and saved to models/ai_model.pkl")

if __name__ == "__main__":
    train_model()
