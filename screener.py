import ccxt
import pandas as pd
import numpy as np
from datetime import datetime


class MultiTimeframeScreener:
    def __init__(self, symbols, timeframes, exchange=None):
        self.exchange = exchange or ccxt.binance({"enableRateLimit": True})
        self.symbols = symbols
        self.timeframes = timeframes

    def fetch_ohlcv(self, symbol, timeframe, limit=100):
        data = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def compute_indicators(self, df):
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(window=20).mean()
        df['bb_expand'] = df['bb_width'] > df['bb_width'].rolling(window=20).mean()

        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        df['volume_avg'] = df['volume'].rolling(window=20).mean()
        return df

    def screen(self):
        result = {}
        for symbol in self.symbols:
            result[symbol] = {}
            for tf in self.timeframes:
                df = self.fetch_ohlcv(symbol, tf)
                df = self.compute_indicators(df)
                latest = df.iloc[-1]
                result[symbol][tf] = {
                    'sma20': latest['sma20'],
                    'sma50': latest['sma50'],
                    'ema20': latest['ema20'],
                    'ema50': latest['ema50'],
                    'rsi': latest['rsi'],
                    'bb_squeeze': bool(latest['bb_squeeze']),
                    'bb_expand': bool(latest['bb_expand']),
                    'macd': latest['macd'],
                    'macd_signal': latest['macd_signal'],
                    'macd_hist': latest['macd_hist'],
                    'volume': latest['volume'],
                    'volume_avg': latest['volume_avg']
                }
        return result

import time
import logging

if __name__ == "__main__":
    logging.basicConfig(
        filename='screener_log.txt',
        filemode='a',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    timeframes = ['5m','15m', '1h', '4h', '1d']
    screener = MultiTimeframeScreener(symbols, timeframes)

    test_cycles = 3  # run 3 quick cycles for testing
    cycle_count = 0

    while True:
        print(f"\n==== Running Screener | Cycle {cycle_count + 1} ====")
        logging.info(f"Running Screener | Cycle {cycle_count + 1}")

        results = screener.screen()

        import os

        os.makedirs("public", exist_ok=True)
        import json

        with open("public/indicators.json", "w") as f:
            json.dump(results, f, indent=2)

        for symbol, tf_data in results.items():
            print(f"\n{symbol}:")
            logging.info(f"{symbol}:")
            for tf, indicators in tf_data.items():
                print(f"  {tf}:")
                logging.info(f"  {tf}:")
                for key, value in indicators.items():
                    print(f"    {key}: {value}")
                    logging.info(f"    {key}: {value}")

        cycle_count += 1

        if cycle_count < test_cycles:
            print("\n==== Waiting 30 seconds (Test Mode) ====\n")
            time.sleep(30)
        else:
            print("\n==== Waiting 5 minutes ====\n")
            time.sleep(300)
