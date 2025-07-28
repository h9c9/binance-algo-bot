import ccxt
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json

# Load symbols and timeframes from your config
with open("adaptive_config.json", "r") as f:
    config = json.load(f)
symbols = list(config.keys())
timeframes = ["5m", "15m", "1h", "4h", "1d"]

def fetch_latest_ohlcv(symbol, timeframe, lookback=500):
    exchange = ccxt.binance()
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=lookback)
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def update_csv(symbol, timeframe):
    filename = f"{symbol.replace('/','')}_{timeframe}.csv"
    # Try to read existing file
    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        old_df['timestamp'] = pd.to_datetime(old_df['timestamp'])
    else:
        old_df = pd.DataFrame()
    # Fetch latest data
    new_df = fetch_latest_ohlcv(symbol, timeframe)
    # Merge and keep only most recent X (usually 500)
    combined = pd.concat([old_df, new_df]).drop_duplicates(subset=["timestamp"])
    combined = combined.sort_values("timestamp")
    # Limit size (optional, eg. 500 rows)
    if len(combined) > 500:
        combined = combined.iloc[-500:]
    combined.to_csv(filename, index=False)
    print(f"Updated {filename} ({len(combined)} rows)")

def main_loop():
    while True:
        now = datetime.now()
        minute = now.minute
        print(f"\n--- Checking at {now} ---")
        # For each timeframe, decide if update is needed
        for tf in timeframes:
            run_this_tf = False
            if tf == "5m"   and minute % 5  == 0: run_this_tf = True
            if tf == "15m"  and minute % 15 == 0: run_this_tf = True
            if tf == "1h"   and minute == 0:      run_this_tf = True
            if tf == "4h"   and now.hour % 4 == 0 and minute == 0: run_this_tf = True
            if tf == "1d"   and now.hour == 0 and minute == 0: run_this_tf = True
            if run_this_tf:
                for symbol in symbols:
                    try:
                        update_csv(symbol, tf)
                    except Exception as e:
                        print(f"Error updating {symbol} {tf}: {e}")
        # Sleep until next minute
        time.sleep(60 - datetime.now().second)

if __name__ == "__main__":
    main_loop()
