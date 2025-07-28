import pandas as pd
import matplotlib.pyplot as plt

filename = 'ohlcv_data/btc_usdt_ohlcv_1h.csv'  # Change as needed

df = pd.read_csv(filename)

# Calculate VWAP
df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
df['cum_vol_tp'] = (df['typical_price'] * df['volume']).cumsum()
df['cum_vol'] = df['volume'].cumsum()
df['vwap'] = df['cum_vol_tp'] / df['cum_vol']

# Calculate moving averages (optional)
df['ma_50'] = df['close'].rolling(window=50).mean()

# Plot
plt.figure(figsize=(15, 6))
plt.plot(df['datetime'], df['close'], label='Close Price', linewidth=1)
plt.plot(df['datetime'], df['ma_50'], label='50-period MA', linewidth=2)
plt.plot(df['datetime'], df['vwap'], label='VWAP', linewidth=2)
plt.title('BTC/USDT 1H - Close, 14 MA, VWAP')
plt.xlabel('Datetime')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.show()
