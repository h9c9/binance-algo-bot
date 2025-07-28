import pandas as pd
import numpy as np
import json
import random
from backtester import Backtester  # reuse your backtester!
import os

# Define parameter ranges for random sampling
param_ranges = {
    "ema_fast": (8, 20),
    "ema_slow": (21, 100),
    "rsi_length": (6, 20),
    "adx_length": (6, 20),
    "vwap_length": (6, 25),
    "volume_zscore": (1.0, 3.0),
    "mean_rev_length": (2, 30),
    # thresholds
    "rsi_overbought": (65, 80),
    "rsi_oversold": (10, 30),
    "adx_threshold": (15, 30),
    "mean_rev_threshold": (0.5, 2.0),
    # weights
    "ema_w": (0.8, 1.5),
    "rsi_w": (0.8, 1.5),
    "adx_w": (0.7, 1.3),
    "vwap_w": (0.8, 1.5),
    "volume_w": (0.6, 1.5),
    "mean_reversion_w": (0.6, 1.5),
    # strategy
    "stoploss": (0.008, 0.025),
    "takeprofit": (0.012, 0.035),
    "trailing": (0.004, 0.012)
}

symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
timeframes = ["5m", "15m", "1h", "4h", "1d"]
data_folder = "./"  # CSV location

config_path = "adaptive_config.json"
trials_per_pair = 100   # Increase for better search

# Utility: sample a config dict
def random_config():
    cfg = {
        "indicators": {
            "ema_fast": random.randint(*param_ranges["ema_fast"]),
            "ema_slow": random.randint(*param_ranges["ema_slow"]),
            "rsi_length": random.randint(*param_ranges["rsi_length"]),
            "adx_length": random.randint(*param_ranges["adx_length"]),
            "vwap_length": random.randint(*param_ranges["vwap_length"]),
            "volume_zscore": round(random.uniform(*param_ranges["volume_zscore"]), 2),
            "mean_rev_length": random.randint(*param_ranges["mean_rev_length"])
        },
        "thresholds": {
            "rsi_overbought": random.randint(*param_ranges["rsi_overbought"]),
            "rsi_oversold": random.randint(*param_ranges["rsi_oversold"]),
            "adx_threshold": random.randint(*param_ranges["adx_threshold"]),
            "mean_rev_threshold": round(random.uniform(*param_ranges["mean_rev_threshold"]), 2)
        },
        "weights": {
            "ema": round(random.uniform(*param_ranges["ema_w"]), 2),
            "rsi": round(random.uniform(*param_ranges["rsi_w"]), 2),
            "adx": round(random.uniform(*param_ranges["adx_w"]), 2),
            "vwap": round(random.uniform(*param_ranges["vwap_w"]), 2),
            "volume": round(random.uniform(*param_ranges["volume_w"]), 2),
            "mean_reversion": round(random.uniform(*param_ranges["mean_reversion_w"]), 2)
        },
        "strategy": {
            "stoploss": round(random.uniform(*param_ranges["stoploss"]), 4),
            "takeprofit": round(random.uniform(*param_ranges["takeprofit"]), 4),
            "trailing": round(random.uniform(*param_ranges["trailing"]), 4)
        }
    }
    return cfg

# Load current config, or initialize
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        best_config = json.load(f)
else:
    best_config = {s: {tf: {} for tf in timeframes} for s in symbols}

results = []

for symbol in symbols:
    for tf in timeframes:
        filename = f"{symbol.replace('/', '')}_{tf}.csv"
        if not os.path.exists(os.path.join(data_folder, filename)):
            print(f"Skipping {symbol} {tf}: data file not found.")
            continue
        print(f"Optimizing {symbol} {tf}")
        best_balance = -float('inf')
        best_cfg = None
        for trial in range(trials_per_pair):
            cfg = random_config()
            bt = Backtester(config_path, symbol, tf, initial_balance=1000)
            # overwrite the config for THIS run with sampled params:
            bt.cfg = cfg
            data = bt.load_data(os.path.join(data_folder, filename))
            trades, balance = bt.run(data, print_trades=False)
            results.append({
                "symbol": symbol, "timeframe": tf, "trial": trial, "balance": balance,
                **{k: v for d in [cfg['indicators'], cfg['thresholds'], cfg['weights'], cfg['strategy']] for k, v in d.items()}
            })
            if balance > best_balance:
                best_balance = balance
                best_cfg = cfg

        if best_cfg:
            if symbol not in best_config:
                best_config[symbol] = {}
            best_config[symbol][tf] = best_cfg
            print(f"Best for {symbol} {tf}: Balance {best_balance:.2f}")

# Save the updated config
with open(config_path, "w") as f:
    json.dump(best_config, f, indent=2)

# Save results as CSV for further analysis or dashboard plotting
results_df = pd.DataFrame(results)
results_df.to_csv("optimization_results.csv", index=False)
print("\nOptimization completed. Results saved to optimization_results.csv and adaptive_config.json.")

