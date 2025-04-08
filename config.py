# File: config.py

#print("[DEBUG] Loaded config.py")

import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

if not CONFIG_PATH.exists():
    raise FileNotFoundError("[CONFIG] Missing config.json. Please create one.")

class Config:
    def __init__(self):
        with open("config.json") as f:
            self.config = json.load(f)
        self.validate_required_keys()

    def get(self, dotted_key: str, default=None):
        keys = dotted_key.split(".")
        val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                print(f"[CONFIG] Key '{dotted_key}' not found.")
                return default
        return val

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
    
    def log_unused_keys(self):
        defined_keys = {
            "telegram", "kraken", "strategy", "discovery", "margin", "paper_trading",
            "user", "summary_time", "summary_retention_days", "train_from_backtest",
            "telegram_enabled", "use_ml_model", "model_version", "trading_rules", "telegram_intervals"
        }
        unused = set(self.config.keys()) - defined_keys
        if unused:
            print(f"[CONFIG] Unused top-level keys: {unused}")

    def _load(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError("Missing config.json file. Please create it before running.")
        with CONFIG_PATH.open() as f:
            return json.load(f)

    def set(self, key: str, value):
        if key in self.config:
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
        return self.config.get("telegram", {})

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

    @property
    def summary_time(self):
        return self.config.get("summary_time", "09:00")

    @property
    def summary_retention_days(self):
        return self.config.get("summary_retention_days", 14)

    @property
    def train_from_backtest(self):
        return self.config.get("train_from_backtest", True)

    @property
    def telegram_enabled(self):
        return self.config.get("telegram_enabled", True)

    @property
    def use_ml_model(self):
        return self.config.get("use_ml_model", False)

    @property
    def model_version(self):
        return self.config.get("model_version", "v1.0")

if __name__ == "__main__":
    cfg = Config()
    print("[TEST] trading_rules.focus_pairs →", cfg.get("trading_rules.focus_pairs", default=[]))
