# File: config.py

import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

class Config:
    def __init__(self):
        self._config = self._load()

    def _load(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError("Missing config.json file. Please create it before running.")
        with CONFIG_PATH.open() as f:
            return json.load(f)

    def get(self, *keys, default=None):
        data = self._config

        # Unpack dot notation: get("telegram.bot_token")
        if len(keys) == 1 and isinstance(keys[0], str) and "." in keys[0]:
            keys = keys[0].split(".")

        for key in keys:
            if isinstance(data, dict) and isinstance(key, str):
                if key in data:
                    data = data[key]
                else:
                    print(f"[CONFIG] Key '{key}' not found.")
                    return default
            else:
                print(f"[CONFIG] Invalid key access: '{key}'")
                return default

        return data if data is not None else default

    @property
    def telegram(self):
        return self._config.get("telegram", {})

    @property
    def kraken(self):
        return self._config.get("kraken", {})

    @property
    def strategy(self):
        return self._config.get("strategy", {})

    @property
    def discovery(self):
        return self._config.get("discovery", {})

    @property
    def margin(self):
        return self._config.get("margin", {})

    @property
    def paper_trading(self):
        return self._config.get("paper_trading", False)

    @property
    def user(self):
        return self._config.get("user", "Daniel")