# File: audit_discovered.py

#print("[DEBUG] Loaded audit_discovered.py")

import json
from pathlib import Path
from kraken_api import KrakenClient

DISCOVERY_FILE = Path("data/discovered_pairs.json")

def audit_discovered():
    if not DISCOVERY_FILE.exists():
        print("No discovered pairs.")
        return

    with open(DISCOVERY_FILE) as f:
        pairs = json.load(f)

    kraken = KrakenClient()
    print(f"🔍 {len(pairs)} discovered pairs loaded:")

    for pair in sorted(pairs):
        try:
            ticker = kraken.get_ticker(pair)
            price = float(ticker['c'].iloc[0][0])
            vol = float(ticker['v'].iloc[1])
            gbp_vol = price * vol
            print(f"{pair:<10} | £{gbp_vol:,.2f} / 24h")
        except Exception as e:
            print(f"{pair:<10} | ERROR: {e}")

if __name__ == "__main__":
    audit_discovered()
