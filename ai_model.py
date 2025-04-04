# File: ai_model.py

import pandas as pd
import numpy as np
import joblib
from kraken_api import KrakenClient
from config import Config
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

config = Config()
USE_ML_MODEL = config.get("use_ml_model", default=False)

kraken = KrakenClient()

# Load model if needed
MODEL = None
if USE_ML_MODEL:
    try:
        MODEL = joblib.load("models/ai_model.pkl")
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
            latest = df.iloc[-1]
            features = pd.DataFrame([{
                "price": latest["close"],
                "hour": latest["time"].hour,
                "weekday": latest["time"].weekday()
            }])
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
