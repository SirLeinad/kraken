# discovery.py
import json
import os
from pipeline import run_pipeline

class PairDiscovery:
    def __init__(self, output_path="data/discovered_pairs.json"):
        self.output_path = output_path
        self.discovered = {}

    def get_eligible_pairs(self):
        # Run ML pipeline to get high-confidence pairs
        self.discovered = run_pipeline()  # returns dict: {pair: score}
        print(f"[DISCOVERY] Pairs from ML: {self.discovered}")
        self.save()

    def save(self):
        with open(self.output_path, "w") as f:
            json.dump(self.discovered, f, indent=2)
