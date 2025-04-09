# file: discovery.py

import os
import json
import time
from datetime import datetime, timedelta

from ai_model import load_model, calculate_confidence
from utils.data_loader import load_ohlcv_csv
from kraken_api import KrakenClient
from config import Config

TTL_HOURS = 24
MAX_DISCOVERED = 10
CONFIDENCE_THRESHOLD = 0.6
DISCOVERY_FILE = "data/discovered_pairs.json"


class PairDiscovery:
    def __init__(self):
        self.config = Config()
        self.kraken = KrakenClient()
        self.model = load_model()
        self.excluded = set(self.config.get("excluded_pairs", []))
        self.discovery_limit = self.config.get("discovery.max_active_pairs", MAX_DISCOVERED)
        self.volume_threshold = self.config.get("discovery.min_volume_24h_gbp", 10000)
        self.allowed_quotes = {"GBP", "USD", "EUR"}
        self.now = datetime.utcnow()

    def run_discovery(self):
        print("[DISCOVERY] Starting autonomous pair scan...")
        tradable = self.kraken.get_tradable_asset_pairs()
        discovered = {}

        for pair in tradable:
            if pair in self.excluded or not pair[-3:] in self.allowed_quotes:
                continue

            try:
                df = load_ohlcv_csv(pair)
                if df is None or len(df) < 5:
                    continue

                confidence = calculate_confidence(df, self.model)
                vol_gbp = self.kraken.estimate_volume_gbp(df)

                if confidence >= CONFIDENCE_THRESHOLD and vol_gbp >= self.volume_threshold:
                    discovered[pair] = {
                        "confidence": confidence,
                        "volume_24h_gbp": vol_gbp,
                        "timestamp": self.now.isoformat()
                    }
            except Exception as e:
                print(f"[DISCOVERY] Failed to evaluate {pair}: {e}")
                continue

        top = dict(sorted(discovered.items(), key=lambda x: x[1]["confidence"], reverse=True)[:self.discovery_limit])
        self._save_discovered(top)
        print(f"[DISCOVERY] Top {len(top)} discovered pairs: {list(top)}")
        return top

    def _save_discovered(self, pairs: dict):
        os.makedirs(os.path.dirname(DISCOVERY_FILE), exist_ok=True)
        with open(DISCOVERY_FILE, "w") as f:
            json.dump(pairs, f, indent=2)

    def load_discovered_pairs(self):
        if not os.path.exists(DISCOVERY_FILE):
            return {}

        with open(DISCOVERY_FILE) as f:
            pairs = json.load(f)

        fresh = {}
        now = datetime.utcnow()
        for pair, data in pairs.items():
            ts = datetime.fromisoformat(data.get("timestamp"))
            if now - ts < timedelta(hours=TTL_HOURS):
                fresh[pair] = data
        return fresh
