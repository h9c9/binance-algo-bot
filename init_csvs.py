from firstudemybot import fetch_btc_ohlcv

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
TIMEFRAMES = ['1m', '5m', '15m', '1h', '1d']

for symbol in SYMBOLS:
    for tf in TIMEFRAMES:
        file_symbol = symbol.replace("/", "_").lower()
        filename = f"{file_symbol}_ohlcv_{tf}.csv"
        print(f"Fetching {symbol} {tf}...")
        try:
            df = fetch_btc_ohlcv(symbol=symbol, timeframe=tf, limit=300)
            df.to_csv(filename, index=False)
            print(f"{filename} initialized with {len(df)} rows.")
        except Exception as e:
            print(f"Error for {symbol} {tf}: {e}")
