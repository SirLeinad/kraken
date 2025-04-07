print("[DEBUG] Loaded export_graph.py")

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def plot_profit_graph():
    if not Path("logs/profit_log.csv").exists():
        print("No profit log found.")
        return
        
    df = pd.read_csv("logs/profit_log.csv", names=[
        "timestamp", "pair", "entry", "exit", "volume", "gain", "reason"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["cumulative"] = df["gain"].cumsum()

    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp"], df["cumulative"], linewidth=2)
    plt.title("📈 Cumulative Profit Over Time")
    plt.xlabel("Time")
    plt.ylabel("Total Profit (£)")
    plt.grid(True)
    plt.tight_layout()
    filename = "logs/profit_chart.png"
    plt.savefig(filename)
    return filename
