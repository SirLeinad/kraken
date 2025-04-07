# File: ai_model.py

import pandas as pd
import numpy as np
import joblib
from kraken_api import KrakenClient
from config import Config
import warnings
import joblib

warnings.filterwarnings("ignore", category=FutureWarning)

config = Config()
USE_ML_MODEL = config.get("use_ml_model", default=False)
MODEL_PATH = "models/model_v1.0.pkl"

kraken = KrakenClient()

# Load model if needed
MODEL = None
if USE_ML_MODEL:
    try:
        MODEL = joblib.load(MODEL_PATH)
        print("✅ ML model loaded for confidence scoring.")
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        MODEL = None

def calculate_confidence(pair: str, interval: int = 60, window: int = 30) -> float:
    try:
        ohlc = kraken.get_ohlc(pair, interval=interval)
        df = ohlc.tail(window).copy()
        if len(df) < 10:
            return 0.0

        df['momentum'] = df['close'].pct_change().fillna(0.0)
        df['momentum'] = df['momentum'].infer_objects(copy=False)

        df['volatility'] = df['close'].rolling(5).std()
        
        df['volume_trend'] = df['volume'].pct_change().fillna(0.0)
        df['volume_trend'] = df['volume_trend'].infer_objects(copy=False)

        mean_close = df['close'].mean()
        if not mean_close or mean_close == 0 or pd.isna(mean_close):
            return 0.0

        if USE_ML_MODEL and MODEL:
            from feature_engineering import compute_rsi, compute_sma

            if "close" not in df.columns:
                print(f"[ERROR] Missing 'close' column for {pair}. Columns present: {df.columns.tolist()}")
                return 0.0

            try:
                latest = df.iloc[-1].copy()
                latest["rsi"] = compute_rsi(df["close"]).iloc[-1]
                latest["sma"] = compute_sma(df["close"]).iloc[-1]
            except Exception as e:
                print(f"[ERROR] Feature computation failed for {pair}: {e}")
                return 0.0

            features = pd.DataFrame([{
                "rsi": latest["rsi"],
                "sma": latest["sma"]
            }])

            if pd.isna(latest["rsi"]) or pd.isna(latest["sma"]):
                return 0.0

            proba = MODEL.predict_proba(features)[0][1]  # prob of buy
            return round(float(proba), 4)

        # fallback to original rule-based
        momentum_score = df['momentum'].mean()
        volatility_score = 1.0 - df['volatility'].mean() / mean_close
        volume_score = df['volume_trend'].mean()

        score = 0.0
        score += np.clip(momentum_score * 5, -1, 1)
        score += np.clip(volatility_score, -1, 1)
        score += np.clip(volume_score * 2, -1, 1)
        score = (score + 3) / 6
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    except Exception as e:
        import traceback
        print(f"[ERROR] AI model failure on {pair}: {e}\n" + traceback.format_exc())
        return 0.0
