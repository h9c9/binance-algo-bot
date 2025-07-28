import pandas as pd
import matplotlib.pyplot as plt

filename = 'ohlcv_data/btc_usdt_ohlcv_5m.csv'  # Change to any symbol/timeframe as needed
df = pd.read_csv(filename)

# Block trade detection parameters
window = 20  # Rolling window for average/standard deviation
block_threshold = 2  # Number of std deviations above mean to call a block

# Calculate rolling mean and std of volume
df['vol_mean'] = df['volume'].rolling(window).mean()
df['vol_std'] = df['volume'].rolling(window).std()

# Detect block trades
df['block_trade'] = (df['volume'] > df['vol_mean'] + block_threshold * df['vol_std'])

# Further classify block trades as buy or sell
df['block_buy'] = df['block_trade'] & (df['close'] > df['open'])
df['block_sell'] = df['block_trade'] & (df['close'] < df['open'])

# Show recent block trades
print("Recent block buys:")
print(df[df['block_buy']].tail(5)[['datetime', 'close', 'volume']])
print("\nRecent block sells:")
print(df[df['block_sell']].tail(5)[['datetime', 'close', 'volume']])

# Plot
plt.figure(figsize=(15, 6))
plt.plot(df['datetime'], df['close'], label='Close Price')
plt.scatter(df[df['block_buy']]['datetime'], df[df['block_buy']]['close'], marker='^', color='lime', label='Block Buy', s=100)
plt.scatter(df[df['block_sell']]['datetime'], df[df['block_sell']]['close'], marker='v', color='red', label='Block Sell', s=100)
plt.title('Block Buys/Sells (Volume Spike Detection)')
plt.xlabel('Datetime')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.show()
