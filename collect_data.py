from firstudemybot import fetch_btc_ohlcv
import pandas as pd
import os
import schedule
import time

def collect_and_append(symbol, timeframe, max_rows=300):
    try:
        df = fetch_btc_ohlcv(symbol=symbol, timeframe=timeframe, limit=1)
        # Create file name like btc_usdt_ohlcv_1m.csv, eth_usdt_ohlcv_5m.csv, etc.
        file_symbol = symbol.replace("/", "_").lower()
        filename = f'{file_symbol}_ohlcv_{timeframe}.csv'
        if os.path.exists(filename):
            existing = pd.read_csv(filename)
            if df['timestamp'][0] not in existing['timestamp'].values:
                updated = pd.concat([existing, df], ignore_index=True)
                # Keep only the last max_rows rows
                if len(updated) > max_rows:
                    updated = updated.iloc[-max_rows:]
                updated.to_csv(filename, index=False)
                print(f"[{symbol} {timeframe}] New data appended. (total rows: {len(updated)})")
            else:
                print(f"[{symbol} {timeframe}] No new data. Already up-to-date.")
        else:
            df.to_csv(filename, index=False)
            print(f"[{symbol} {timeframe}] File created and data written.")
    except Exception as e:
        print(f"[{symbol} {timeframe}] Error: {e}")

# List your symbols here
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
TIMEFRAMES = ['1m', '5m', '15m', '1h', '1d']

def schedule_all_symbols_timeframes():
    # Schedule each timeframe at its proper interval for all symbols
    for symbol in SYMBOLS:
        schedule.every(1).minutes.do(lambda sym=symbol: collect_and_append(sym, '1m'))
        schedule.every(5).minutes.do(lambda sym=symbol: collect_and_append(sym, '5m'))
        schedule.every(15).minutes.do(lambda sym=symbol: collect_and_append(sym, '15m'))
        schedule.every().hour.at(":00").do(lambda sym=symbol: collect_and_append(sym, '1h'))
        schedule.every().day.at("00:00").do(lambda sym=symbol: collect_and_append(sym, '1d'))

if __name__ == '__main__':
    print("Starting multi-symbol, multi-timeframe, rolling-window collection. Press Ctrl+C to stop.")

    schedule_all_symbols_timeframes()

    while True:
        schedule.run_pending()
        time.sleep(10)
