import pandas as pd
import numpy as np
import json
import os
from tqdm import tqdm
from binance_weighted_algo import BinanceWeightedAlgoTrader

import os

# DEBUG: List your data files
print("Current directory:", os.getcwd())
print('Files in ohlcv_data:', os.listdir('./ohlcv_data'))


# ---- USER SETTINGS ----
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
timeframes = ["5m", "15m", "1h", "4h", "1d"]
data_path = "./ohlcv_data"  # Or "." if files are in same folder as script
config_path = "adaptive_config.json"
initial_balance = 1000

# ---- UTILS ----
def get_csv_filename(symbol, tf):
    s = symbol.lower().replace("/", "_")
    return f"{s}_ohlcv_{tf}.csv"

def run_single_backtest(csv_path, symbol, tf, cfg):
    try:
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        print(f"Failed to load {csv_path}: {e}")
        return None

    bot = BinanceWeightedAlgoTrader(
        api_key="", secret="",
        symbols=[symbol], timeframes=[tf],
        config_path=config_path
    )

    this_cfg = cfg[symbol][tf]
    df = bot.calculate_indicators(df, this_cfg)

    balance = initial_balance
    position = 0
    entry_price = 0
    last_signal = "none"
    trades = []

    for i in range(50, len(df)):
        row = df.iloc[:i+1]
        score = bot.score_signal(row, this_cfg)
        signal = "buy" if score > 1 else "sell" if score < -1 else "avoid"
        price = row.iloc[-1]['close']

        if position == 0 and signal in ["buy", "sell"] and signal != last_signal:
            position = 1 if signal == "buy" else -1
            entry_price = price
            trades.append({"entry_time": row.iloc[-1]['timestamp'], "entry_price": entry_price, "side": signal})
        if position != 0:
            stoploss = entry_price * (1 - this_cfg["strategy"]["stoploss"] if position == 1 else 1 + this_cfg["strategy"]["stoploss"])
            takeprofit = entry_price * (1 + this_cfg["strategy"]["takeprofit"] if position == 1 else 1 - this_cfg["strategy"]["takeprofit"])
            if (position == 1 and (price <= stoploss or price >= takeprofit or signal == "sell")) or \
               (position == -1 and (price >= stoploss or price <= takeprofit or signal == "buy")):
                pnl = (price - entry_price) * position
                balance += pnl
                trades[-1].update({
                    "exit_time": row.iloc[-1]['timestamp'],
                    "exit_price": price,
                    "pnl": pnl
                })
                position = 0
                entry_price = 0
        last_signal = signal

    net_return = balance - initial_balance
    n_trades = len([t for t in trades if "pnl" in t])
    win_trades = len([t for t in trades if "pnl" in t and t["pnl"] > 0])
    win_rate = (win_trades / n_trades) * 100 if n_trades else 0

    return {
        "symbol": symbol,
        "timeframe": tf,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "final_balance": balance,
        "net_return": net_return,
        "all_trades": trades
    }

# ---- MAIN BATCH LOOP ----
if __name__ == "__main__":
    with open(config_path, "r") as f:
        cfg = json.load(f)
    all_results = []

    print(f"Batch backtesting {len(symbols) * len(timeframes)} pairs ...")
    for symbol in tqdm(symbols):
        for tf in timeframes:
            csv_file = get_csv_filename(symbol, tf)
            csv_path = os.path.join(data_path, csv_file)
            if not os.path.isfile(csv_path):
                print(f"Missing: {csv_path}")
                continue
            result = run_single_backtest(csv_path, symbol, tf, cfg)
            if result:
                all_results.append(result)

    if all_results:
        df = pd.DataFrame([
            {
                "Symbol": r["symbol"],
                "Timeframe": r["timeframe"],
                "Trades": r["n_trades"],
                "WinRate": f"{r['win_rate']:.1f}%",
                "NetReturn": f"{r['net_return']:.2f}",
                "FinalBalance": f"{r['final_balance']:.2f}"
            }
            for r in all_results
        ])
        df.to_csv("batch_backtest_results.csv", index=False)
        print("Results saved to batch_backtest_results.csv")
        print(df)
    else:
        print("No results to save. Please check your CSV files.")
