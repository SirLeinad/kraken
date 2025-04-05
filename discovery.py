# File: discovery.py

import json
from datetime import datetime
from pathlib import Path
from config import Config
from train_pipeline import run_pipeline
from kraken_api import get_price_history  # Assumes this returns OHLCV DataFrame

class PairDiscovery:
    def __init__(self):
        self.output_path = Path("data/discovered_pairs.json")
        self.config = Config()
        self.conf_threshold = self.config.get("strategy.min_confidence", 0.8)
        self.max_volatility = self.config.get("discovery.max_volatility", 0.15)

    def get_eligible_pairs(self):
        print("[DISCOVERY] Running pipeline...")
        results = run_pipeline(conf_threshold=self.conf_threshold)
        self.discovered = {}

        for pair, score in results.items():
            if score < self.conf_threshold:
                continue
            vol = self.get_pair_volatility(pair)
            if vol is None:
                continue
            if vol > self.max_volatility:
                print(f"[DISCOVERY] Skipping {pair} due to high volatility ({vol:.2f})")
                continue
            self.discovered[pair] = score

        print(f"[DISCOVERY] Selected pairs: {list(self.discovered)}")
        self.save()
        return self.discovered

    def get_pair_volatility(self, pair):
        try:
            df = get_price_history(pair)  # Should return DataFrame with 'close'
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
