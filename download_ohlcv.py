import ccxt
import pandas as pd
import os

symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
timeframes = ["5m", "15m", "1h", "4h", "1d"]  # <-- Add "4h" here
limit = 1000  # or as needed

path = "./ohlcv_data"
os.makedirs(path, exist_ok=True)

exchange = ccxt.binance()

for symbol in symbols:
    for tf in timeframes:
        filename = f"{symbol.lower().replace('/', '_')}_ohlcv_{tf}.csv"
        file_path = os.path.join(path, filename)
        print(f"Downloading {symbol} {tf} ...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.to_csv(file_path, index=False)
        print(f"Saved {file_path}")
