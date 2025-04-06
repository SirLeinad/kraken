# File: discovery.py

import json
from datetime import datetime
from pathlib import Path
from config import Config
from train_pipeline import run_pipeline
from kraken_api import KrakenClient  # Assumes this returns OHLCV DataFrame

class PairDiscovery:
    def __init__(self):
        self.output_path = Path("data/discovered_pairs.json")
        self.config = Config()
        self.conf_threshold = self.config.get("strategy.min_confidence", 0.8)

    def get_24h_volume_gbp(pair):
        try:
            ticker = KrakenClient().get_ticker(pair)
            price = float(ticker["c"].iloc[0][0])
            vol = float(ticker["v"].iloc[0][1])  # 24h vol
            return price * vol
        except Exception as e:
            print(f"[VOL24H] Error loading volume for {pair}: {e}")
            return 0

    def get_eligible_pairs(self):
        print("[DISCOVERY] Running pipeline...")
        results = run_pipeline(conf_threshold=self.conf_threshold)
        
        self.discovered = {}
        self.min_volume_gbp = self.config.get("discovery.min_volume_24h_gbp", 100000)
        self.max_volatility = self.config.get("discovery.max_volatility", 0.15)

        for pair, score in results.items():
            if get_24h_volume_gbp(pair) < min_vol_gbp:
                print(f"[DISCOVERY] Skipping {pair} due to low volume")
                continue
            if score < self.conf_threshold:
                continue
            vol = self.get_pair_volatility(pair)
            if vol is None:
                continue
            if vol > self.max_volatility:
                print(f"[DISCOVERY] Skipping {pair} due to high volatility ({vol:.2f})")
                continue
            self.discovered[pair] = score

        max_pairs = self.config.get("discovery.max_active_pairs")
        if max_pairs and len(self.discovered) > max_pairs:
            top_pairs = sorted(self.discovered.items(), key=lambda x: x[1], reverse=True)[:max_pairs]
            self.discovered = dict(top_pairs)
            print(f"[DISCOVERY] Trimmed to top {max_pairs} pairs")

        self.save()
        return self.discovered

    def get_pair_volatility(self, pair):
        try:
            df = KrakenClient.get_price_history(pair)  # Should return DataFrame with 'close'
            returns = df['close'].pct_change().dropna()
            return returns.std()
        except Exception as e:
            print(f"[VOL] Error for {pair}: {e}")
            return None

    def save(self):
        data = {
            "last_updated": datetime.utcnow().isoformat(),
            "model_version": self.config.get("model_version", "v1.0"),
            "pairs": self.discovered
        }
        with self.output_path.open("w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    discovery = PairDiscovery()
    discovery.get_eligible_pairs()
