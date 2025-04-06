def engineer_features_from_ohlcv(df):
    # Basic placeholder logic — customize this
    df["sma"] = df["close"].rolling(window=10).mean()
    df["rsi"] = compute_rsi(df["close"])
    df = df.dropna()
    X = df[["sma", "rsi"]]
    y = (df["close"].shift(-1) > df["close"]).astype(int)
    return X, y

def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))