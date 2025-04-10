#print("[DEBUG] Loaded feature_engineering.py")

import pandas as pd

def engineer_features_from_ohlcv(df):
    import warnings
    warnings.filterwarnings("ignore")

    if df.empty or "close" not in df.columns:
        raise ValueError("❌ Input OHLCV data missing 'close' column")

    features = {}
    errors = []

    try:
        features["sma"] = df["close"].rolling(window=10).mean()
    except Exception as e:
        errors.append(f"sma: {e}")

    try:
        features["rsi"] = compute_rsi(df)
    except Exception as e:
        print(f"[RSI FAIL] {e}")
        raise


    if not features:
        raise ValueError("❌ No features could be engineered.")

    df_feat = df.copy()

    for name, series in features.items():
        df_feat[name] = series

    df_feat = df_feat.dropna()

    if "close" not in df_feat.columns:
        print(f"[ERROR] 'close' missing after dropna(). Columns: {df_feat.columns.tolist()}")
        print(df_feat.head(3).to_string())
        raise ValueError("❌ 'close' column dropped unexpectedly")

    X = df_feat[list(features.keys())]
    y = (df_feat["close"].shift(-1) > df_feat["close"]).astype(int)

    if len(X) != len(y):
        X = X[:-1]
        y = y.dropna()

    if len(X) == 0 or len(y) == 0:
        raise ValueError("❌ Feature engineering returned no data.")

    return X, y

def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if "close" not in df.columns:
        print(f"[RSI] ERROR: 'close' column missing in input to compute_rsi(). Columns: {df.columns.tolist()}")
        raise KeyError("Missing 'close' in compute_rsi input")

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_sma(close: pd.Series, period: int = 10) -> pd.Series:
    return close.rolling(window=period).mean()