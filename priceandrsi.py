import pandas as pd
import matplotlib.pyplot as plt

filename = 'ohlcv_data/btc_usdt_ohlcv_1h.csv'  # Change as needed
df = pd.read_csv(filename)

# Calculate RSI (14)
period = 14
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Optional: Calculate a moving average for price panel
df['ma_50'] = df['close'].rolling(window=50).mean()

# Plot with two panels
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

# Price chart (upper)
ax1.plot(df['datetime'], df['close'], label='Close', color='blue')
ax1.plot(df['datetime'], df['ma_50'], label='50-period MA', color='orange', linewidth=1.5)
ax1.set_title('BTC/USDT 1H Price & RSI')
ax1.set_ylabel('Price')
ax1.legend(loc='upper left')
ax1.grid(True)

# RSI chart (lower)
ax2.plot(df['datetime'], df['rsi'], label='RSI (14)', color='purple')
ax2.axhline(70, color='red', linestyle='--', label='Overbought (70)')
ax2.axhline(30, color='green', linestyle='--', label='Oversold (30)')
ax2.set_ylabel('RSI')
ax2.set_xlabel('Datetime')
ax2.legend(loc='upper left')
ax2.grid(True)

plt.tight_layout()
plt.show()
