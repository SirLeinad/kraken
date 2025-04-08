# File: ai_model.py

#print("[DEBUG] Loaded ai_model.py")

import pandas as pd
import numpy as np
import joblib
from kraken_api import KrakenClient
from config import Config
import warnings
import xgboost as xgb

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
        print(f"[XGBOOST] Booster backend: {MODEL.get_booster().attributes()}")
        #booster = MODEL.get_booster()
        #print(f"[XGBOOST] Raw booster config:")
        #print(booster.save_config())  # This shows exact params including predictor, device, method

    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        MODEL = None

def calculate_confidence(pair: str, interval: int = 1, window: int = 30) -> float:
    try:
        interval = config.get("strategy.confidence_interval", default=1)
        ohlc = kraken.get_ohlc(pair, interval=interval)

        #print(f"[TRACE] Raw OHLC df for {pair} → shape: {ohlc.shape}, columns: {ohlc.columns.tolist()}")
        #print(ohlc.head(3).to_string())

        df = ohlc.tail(window).copy()

        if df.empty:
            print(f"[ERROR] DataFrame empty for {pair} in calculate_confidence()")
            return 0.0

        if "close" not in df.columns:
            print(f"[ERROR] Missing 'close' column for {pair}. Columns: {df.columns.tolist()}")
            print(df.head(3).to_string())
            return 0.0

        if len(df) < 10:
            return 0.0

        df['momentum'] = df['close'].pct_change().fillna(0.0)
        df['momentum'] = df['momentum'].infer_objects(copy=False)

        df['volatility'] = df['close'].rolling(5).std()
        with np.errstate(divide='ignore', invalid='ignore'):
            df['volume_trend'] = df['volume'].pct_change().replace([np.inf, -np.inf], 0).fillna(0.0)
        df['volume_trend'] = df['volume_trend'].infer_objects(copy=False)

        mean_close = df['close'].mean()
        if not mean_close or mean_close == 0 or pd.isna(mean_close):
            return 0.0

        if USE_ML_MODEL and MODEL:
            from feature_engineering import compute_rsi, compute_sma

            try:
                latest = df.iloc[-1].copy()
                latest["rsi"] = compute_rsi(df).iloc[-1]
                latest["sma"] = compute_sma(df["close"]).iloc[-1]
            except Exception as e:
                print(f"[ERROR] Feature computation failed for {pair}: {e}")
                return 0.0

            if pd.isna(latest["rsi"]) or pd.isna(latest["sma"]):
                return 0.0

            features = pd.DataFrame([[latest["sma"], latest["rsi"]]], columns=["sma", "rsi"])
            features = features.astype(np.float32)  
            
            if not hasattr(calculate_confidence, "_last_features"):
                calculate_confidence._last_features = {}
            key = f"{pair}_features"
            current = features.to_dict(orient="records")[0]
            previous = calculate_confidence._last_features.get(key)
            if previous == current:
                print(f"[NO CHANGE] Features unchanged for {pair}")
            else:
                print(f"[FEATURES] {pair} → {current}")
                calculate_confidence._last_features[key] = current

            print(f"[FEATURES] {pair} input → {features.to_dict(orient='records')}")
            with open("logs/ai_feature_inputs.csv", "a") as f:
                # Log with extra metadata
                features["pair"] = pair
                features["timestamp"] = pd.Timestamp.utcnow()
                features.to_csv("logs/ai_feature_inputs.csv", header=False, index=False, mode="a")
                features = features.drop(columns=["pair", "timestamp"])
            proba = MODEL.predict_proba(features)[0][1]
            return round(float(proba), 4)

        # Compute improved momentum across window
        momentum_score = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]

        # Compute volatility as mean of rolling 5-return stddev
        volatility_score = df['close'].pct_change().rolling(5).std().mean()

        # Fix volume anomaly
        with np.errstate(divide='ignore', invalid='ignore'):
            df['volume_trend'] = df['volume'].pct_change().replace([np.inf, -np.inf], 0).fillna(0.0)

        volume_score = df['volume_trend'].mean()

        # Normalize all to 0–1 scale
        momentum_norm = np.clip((momentum_score + 0.02) / 0.04, 0, 1)
        volatility_norm = np.clip(volatility_score / 0.005, 0, 1)
        volume_norm = np.clip((volume_score + 0.1) / 0.2, 0, 1)

        # Weighted average
        score = round(float(momentum_norm * 0.4 + volatility_norm * 0.3 + volume_norm * 0.3), 4)

        # Debug log
        #print(f"[DEBUG] Fallback scores for {pair}")
        #print(f"  momentum_raw:  {momentum_score:.5f}")
        #print(f"  volatility_std: {volatility_score:.5f}")
        #print(f"  volume_raw:    {volume_score:.5f}")
        #print(f"  normalized:    momentum={momentum_norm:.2f}, vol={volatility_norm:.2f}, volume={volume_norm:.2f}")
        #print(f"  final score:   {score:.4f}")

        return round(float(np.clip(score, 0.0, 1.0)), 4)

    except Exception as e:
        import traceback
        print(f"[ERROR] AI model failure on {pair}: {e}\n" + traceback.format_exc())
        return 0.0
