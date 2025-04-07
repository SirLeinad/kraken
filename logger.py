print("[DEBUG] Loaded logger.py")

import json
from datetime import datetime

def log_trade_result(pair, action, volume, entry_price, exit_price, pnl, model=None, confidence=None):
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "pair": pair,
        "action": action,
        "volume": volume,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": pnl,
        "model": model,
        "confidence": confidence
    }
    try:
        with open("data/trade_history.json", "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[LOG] Failed to log trade: {e}")
