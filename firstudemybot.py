
from connect_to_binance import connect_binance
import pandas as pd

def fetch_btc_ohlcv(symbol='BTC/USDT', timeframe='1h', limit=300):
    """
    Fetch historical OHLCV data for a symbol from Binance using CCXT.
    :param symbol: Trading pair symbol (default 'BTC/USDT')
    :param timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')
    :param limit: Number of data points to fetch (default 300)
    :return: DataFrame with historical data
    """
    exchange = connect_binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

    #if __name__ == '__main__':
        #SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
        #TIMEFRAMES = ['1m', '5m', '15m', '1h', '1d']
        #for symbol in SYMBOLS:
          #  for tf in TIMEFRAMES:
           #     df = fetch_btc_ohlcv(symbol=symbol, timeframe=tf, limit=300)
            #    file_symbol = symbol.replace("/", "_").lower()
             #   df.to_csv(f'{file_symbol}_ohlcv_{tf}.csv', index=False)
              #  print(f"{file_symbol}_ohlcv_{tf}.csv initialized with {len(df)} rows")

    # OPTIONAL: Fetch for multiple timeframes at once
    # Uncomment below if you want to create files for all timeframes
    """
    timeframes = ['1m', '5m', '15m', '1h', '1d']
    for tf in timeframes:
        df = fetch_btc_ohlcv(symbol='BTC/USDT', timeframe=tf, limit=300)
        print(f"Fetched {len(df)} rows for {tf}")
        df.to_csv(f'btc_usdt_ohlcv_{tf}.csv', index=False)
    """
