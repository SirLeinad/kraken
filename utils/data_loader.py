import pandas as pd
from pathlib import Path

def load_ohlcv_csv(pair: str, timeframe: str = "1") -> pd.DataFrame:
    """
    Load OHLCVT data from Kraken dump.
    Example: pair='XBTUSD', timeframe='1' (1m), '60' (1h), '1440' (1d)
    """
    file_path = Path(f"data/ohlcv/{pair}_{timeframe}.csv")
    if not file_path.exists():
        raise FileNotFoundError(f"Missing CSV: {file_path}")

    df = pd.read_csv(file_path, header=None,
                     names=["timestamp", "open", "high", "low", "close", "volume", "trades"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.set_index("timestamp", inplace=True)
    return df

