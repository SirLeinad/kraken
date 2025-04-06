# File: config.py

import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

class Config:
    def __init__(self, path="config.json"):
        with open(path) as f:
            self.config = json.load(f)
        self.validate_required_keys()

    def get(self, dotted_key, default=None):
        keys = dotted_key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                print(f"[CONFIG] Key '{dotted_key}' not found.")
                return default
        return value

    def validate_required_keys(self):
        required_keys = [
            "strategy.min_confidence",
            "strategy.stop_loss_pct",
            "strategy.take_profit_pct",
            "strategy.exit_below_ai_score",
            "strategy.pair_trade_cooldown_sec",
            "discovery.interval_hours",
            "discovery.max_volatility"
        ]
        for key in required_keys:
            if self.get(key, None) is None:
                raise ValueError(f"[CONFIG] Required key missing or invalid: {key}")

    def _load(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError("Missing config.json file. Please create it before running.")
        with CONFIG_PATH.open() as f:
            return json.load(f)

    def set(self, key: str, value):
        if key in self._config:
            self.config[key] = value
        else:
            print(f"[CONFIG] Set new key: {key}")
            self.config[key] = value
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=2)
            print(f"[CONFIG] Updated {key} = {value}")
        except Exception as e:
            print(f"[CONFIG] Failed to persist config: {e}")

    @property
    def telegram(self):
        return self._config.get("telegram", {})

    @property
    def kraken(self):
        return self.config.get("kraken", {})

    @property
    def strategy(self):
        return self.config.get("strategy", {})

    @property
    def discovery(self):
        return self.config.get("discovery", {})

    @property
    def margin(self):
        return self.config.get("margin", {})

    @property
    def paper_trading(self):
        return self.config.get("paper_trading", False)

    @property
    def user(self):
        return self.config.get("user", "Daniel")

if __name__ == "__main__":
    cfg = Config()
    print("[TEST] trading_rules.focus_pairs →", cfg.get("trading_rules.focus_pairs", default=[]))
