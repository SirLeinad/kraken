def engineer_features_from_ohlcv(df):
    # Basic placeholder logic — customize this
    df["sma"] = df["close"].rolling(window=10).mean()
    df["rsi"] = compute_rsi(df["close"])
    df = df.dropna()
    X = df[["sma", "rsi"]]
    y = (df["close"].shift(-1) > df["close"]).astype(int)
    return X, y