# File: discovery.py

import pandas as pd
import json
import os
from pathlib import Path
from kraken_api import KrakenClient
from config import Config
from telegram_notifications import *

config = Config()
kraken = KrakenClient()

DISCOVERY_ENABLED = config.discovery['enabled']
MIN_VOLUME = config.discovery['min_volume_24h_gbp']
MAX_ACTIVE = config.discovery.get('max_active_pairs', 10)
EXCLUDED = set(config.strategy['excluded_pairs'])
USER = config.user

DISCOVERY_FILE = Path("data/discovered_pairs.json")
DISCOVERY_FILE.parent.mkdir(exist_ok=True)

class PairDiscovery:
    def __init__(self):
        self.pairs = kraken.get_tradable_asset_pairs()
        self.focus = set(config.strategy['focus_pairs'])
        self.discovered = self.load_discovered()

    def load_discovered(self):
        if DISCOVERY_FILE.exists():
            with open(DISCOVERY_FILE) as f:
                return set(json.load(f))
        return set()

    def save_discovered(self):
        with open(DISCOVERY_FILE, "w") as f:
            json.dump(sorted(self.discovered), f, indent=2)

    def get_eligible_pairs(self):
        eligible = []
        for pair, data in self.pairs.iterrows():
            if not any(ccy in pair for ccy in ["GBP", "USD", "EUR"]):
                continue
            if pair in EXCLUDED or pair in self.focus:
                continue
            try:
                ticker = kraken.get_ticker(pair)
                price = float(ticker['c'].iloc[0][0])
                vol = float(ticker['v'].iloc[1])
                volume_gbp = price * vol
                if volume_gbp > MIN_VOLUME:
                    eligible.append((pair, volume_gbp))
            except Exception:
                continue
        return eligible

    def suggest_new_pairs(self):
        if not DISCOVERY_ENABLED:
            return

        current_total = len(self.focus) + len(self.discovered)
        available_slots = MAX_ACTIVE - len(self.focus)

        # Get current eligible list
        eligible = sorted(self.get_eligible_pairs(), key=lambda x: -x[1])

        added, removed = [], []

        for pair, volume in eligible:
            if len(self.discovered) >= available_slots:
                break
            if pair not in self.discovered:
                self.discovered.add(pair)
                added.append(pair)

        # Clean out discovered pairs with low volume now
        for pair in list(self.discovered):
            try:
                ticker = kraken.get_ticker(pair)
                price = float(ticker['c'].iloc[0][0])
                vol = float(ticker['v'].iloc[1])
                if price * vol < MIN_VOLUME:
                    self.discovered.remove(pair)
                    removed.append(pair)
            except Exception:
                continue

        self.save_discovered()

        if added or removed:
            lines = []
            if added:
                lines.append(f"🆕 Discovered: {', '.join(added)}")
            if removed:
                lines.append(f"🗑 Removed: {', '.join(removed)}")
            print(f'[DISCOVERY] New: {added}, Removed: {removed}')
            discovery_update_notification(USER, added, removed)
        else:
            notify(f"{USER}: No new eligible discovery pairs.", key="discovery", priority="low")
