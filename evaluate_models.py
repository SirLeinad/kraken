# File: evaluate_models.py

print("[DEBUG] Loaded evaluate_models.py")

import json
from collections import defaultdict
from pathlib import Path

def compare_model_performance(trade_log="data/trade_history.json"):
    scores = defaultdict(list)

    path = Path(trade_log)
    if not path.exists():
        return {"error": "No trade log found."}

    with path.open() as f:
        for line in f:
            try:
                t = json.loads(line)
                if 'model' in t and 'pnl' in t:
                    scores[t['model']].append(t['pnl'])
            except json.JSONDecodeError:
                continue

    summary = {}
    for model, trades in scores.items():
        summary[model] = {
            "count": len(trades),
            "avg_pnl": round(sum(trades) / len(trades), 4) if trades else 0.0,
            "total_pnl": round(sum(trades), 4)
        }

    return summary

if __name__ == "__main__":
    from pprint import pprint
    pprint(compare_model_performance())

# Useage: python evaluate_models.py