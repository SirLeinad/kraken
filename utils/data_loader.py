import pandas as pd
from pathlib import Path

def load_ohlcv_csv(pair: str, timeframe: str = "1") -> pd.DataFrame:
    file_path = Path(f"data/ohlcv/{pair}_{timeframe}.csv")
    if not file_path.exists():
        raise FileNotFoundError(f"Missing CSV: {file_path}")

    df = pd.read_csv(
        file_path,
        header=0,  # <-- detect real headers
        names=["timestamp", "open", "high", "low", "close", "volume", "trades"],
        on_bad_lines="skip"
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.set_index("timestamp", inplace=True)
    return df