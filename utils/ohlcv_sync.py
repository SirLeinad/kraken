import pandas as pd
from pathlib import Path
from utils.data_loader import load_ohlcv_csv
from utils.ohlcv_sync import sync_all_ohlcv
from kraken_api import KrakenClient
from datetime import datetime
import re

def get_all_csv_pairs(folder="data/ohlcv"):
    return sorted([f.name for f in Path(folder).glob("*.csv")])

def parse_pair_and_timeframe(filename):
    match = re.match(r"([A-Z]+)_([0-9]+)\.csv", filename)
    if match:
        return match.group(1), match.group(2)
    return None, None

def update_ohlcv_file(pair: str, timeframe: str):
    filepath = Path(f"data/ohlcv/{pair}_{timeframe}.csv")
    try:
        existing = load_ohlcv_csv(pair, timeframe)
        last_ts = existing.index.max()
        start_time = int(last_ts.timestamp())
    except Exception:
        existing = pd.DataFrame()
        start_time = int((datetime.utcnow() - pd.Timedelta(days=5)).timestamp())

    kraken = KrakenClient()
    try:
        df_new = kraken.get_ohlcv(pair, interval=int(timeframe), since=start_time)
        if df_new.empty:
            print(f"[SYNC] No new candles for {pair}_{timeframe}")
            return False

        df_combined = pd.concat([existing, df_new]).drop_duplicates().sort_index()
        df_combined.to_csv(filepath, header=False)
        print(f"[SYNC] Updated {pair}_{timeframe} with {len(df_new)} new rows.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update {pair}_{timeframe}: {e}")
        return False

def sync_all_ohlcv(folder="data/ohlcv"):
    updated = []
    for filename in get_all_csv_pairs(folder):
        pair, tf = parse_pair_and_timeframe(filename)
        if pair and tf:
            success = update_ohlcv_file(pair, tf)
            if success:
                updated.append(f"{pair}_{tf}")
    return updated