import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import time
import logging

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

    def generate_signal(self, multi_tf_data):
        signal_summary = {}
        for symbol, tf_data in multi_tf_data.items():
            try:
                tf5 = tf_data.get('5m', {})
                tf15 = tf_data.get('15m', {})
                tf1h = tf_data.get('1h', {})
                tf4h = tf_data.get('4h', {})

                # Score 10 parameters (trend + entry signals)
                long_score = 0
                long_reasons = []
                short_score = 0
                short_reasons = []

                # Trend checks (4h and 1h EMA)
                if tf4h.get('ema20', 0) > tf4h.get('ema50', 0):
                    long_score += 1
                    long_reasons.append("4h EMA20 > EMA50 (uptrend)")
                else:
                    short_score += 1
                    short_reasons.append("4h EMA20 < EMA50 (downtrend)")

                if tf1h.get('ema20', 0) > tf1h.get('ema50', 0):
                    long_score += 1
                    long_reasons.append("1h EMA20 > EMA50 (uptrend)")
                else:
                    short_score += 1
                    short_reasons.append("1h EMA20 < EMA50 (downtrend)")

                # 15m checks
                if tf15.get('rsi', 0) > 50:
                    long_score += 1
                    long_reasons.append("15m RSI > 50")
                else:
                    short_score += 1
                    short_reasons.append("15m RSI < 50")

                if tf15.get('macd_hist', 0) > 0:
                    long_score += 1
                    long_reasons.append("15m MACD histogram > 0")
                else:
                    short_score += 1
                    short_reasons.append("15m MACD histogram < 0")

                if tf15.get('volume', 0) > tf15.get('volume_avg', 0):
                    long_score += 1
                    long_reasons.append("15m volume > average")
                else:
                    short_score += 1
                    short_reasons.append("15m volume <= average")

                if tf15.get('ema20', 0) > tf15.get('ema50', 0):
                    long_score += 1
                    long_reasons.append("15m EMA20 > EMA50")
                else:
                    short_score += 1
                    short_reasons.append("15m EMA20 < EMA50")

                # 5m checks
                if tf5.get('rsi', 0) > 50:
                    long_score += 1
                    long_reasons.append("5m RSI > 50")
                else:
                    short_score += 1
                    short_reasons.append("5m RSI < 50")

                if tf5.get('macd_hist', 0) > 0:
                    long_score += 1
                    long_reasons.append("5m MACD histogram > 0")
                else:
                    short_score += 1
                    short_reasons.append("5m MACD histogram < 0")

                if tf5.get('volume', 0) > tf5.get('volume_avg', 0):
                    long_score += 1
                    long_reasons.append("5m volume > average")
                else:
                    short_score += 1
                    short_reasons.append("5m volume <= average")

                if tf5.get('ema20', 0) > tf5.get('ema50', 0):
                    long_score += 1
                    long_reasons.append("5m EMA20 > EMA50")
                else:
                    short_score += 1
                    short_reasons.append("5m EMA20 < EMA50")

                # Determine signal based on score
                max_score = 10
                if long_score >= 7:
                    signal_summary[symbol] = {
                        'signal': 'long',
                        'confidence': f"{long_score}/{max_score}",
                        'reasons': long_reasons,
                        'entry_timeframe': '5m or 15m',
                        'strategy': "Trend-following entry after multi-timeframe confirmation"
                    }
                elif short_score >= 7:
                    signal_summary[symbol] = {
                        'signal': 'short',
                        'confidence': f"{short_score}/{max_score}",
                        'reasons': short_reasons,
                        'entry_timeframe': '5m or 15m',
                        'strategy': "Trend-following entry after multi-timeframe confirmation"
                    }
                else:
                    score = max(long_score, short_score)
                    reasons = long_reasons if long_score >= short_score else short_reasons
                    signal_summary[symbol] = {
                        'signal': 'neutral',
                        'confidence': f"{score}/{max_score}",
                        'reasons': reasons,
                        'entry_timeframe': None,
                        'strategy': 'No confirmed setup'
                    }
            except Exception as e:
                signal_summary[symbol] = dict(signal='error', confidence='0/10', reasons=[str(e)], entry_timeframe=None,
                                              strategy='Error in evaluation')
        return signal_summary

if __name__ == "__main__":
    import json
    import os
    import time

    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    timeframes = ['5m', '15m', '1h', '4h', '1d']

    screener = MultiTimeframeScreener(symbols, timeframes)

    os.makedirs("public", exist_ok=True)

    while True:
        results = screener.screen()
        signals = screener.generate_signal(results)

        with open("public/signals.json", "w") as f:
            json.dump(signals, f, indent=2)

        print("✅ signals.json updated.")
        time.sleep(300)  # wait 5 minutes before next update

for symbol, signal in signals.items():
    if signal['signal'] in ['long', 'short'] and int(signal['confidence'].split('/')[0]) >= 7:
        entry_price = exchange.fetch_ticker(symbol)['last']

        trade_data = {
            "symbol": symbol,
            "direction": signal['signal'],
            "entry_price": entry_price,
            "confidence": signal['confidence'],
            "status": "open"
        }

        # For paper trading, simply record the trade instead of placing live orders
        record_trade(trade_data)
        print(f"🚨 {signal['signal'].upper()} (Paper) trade recorded for {symbol} at {entry_price}")

import json

def record_trade(trade_data, status='open'):
    trades_file = 'public/trades.json'
    trades = []
    if os.path.exists(trades_file):
        with open(trades_file, 'r') as f:
            trades = json.load(f)

    trade_data['status'] = status
    trade_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trades.append(trade_data)

    with open(trades_file, 'w') as f:
        json.dump(trades, f, indent=2)
