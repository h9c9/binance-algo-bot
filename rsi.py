import pandas as pd
import matplotlib.pyplot as plt

filename = 'ohlcv_data/btc_usdt_ohlcv_1h.csv'  # Use any timeframe/symbol file

df = pd.read_csv(filename)

# --- RSI calculation ---
period = 14

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# --- Plot RSI ---
plt.figure(figsize=(15, 4))
plt.plot(df['datetime'], df['rsi'], label='RSI (14)', color='purple')
plt.axhline(70, color='red', linestyle='--', label='Overbought (70)')
plt.axhline(30, color='green', linestyle='--', label='Oversold (30)')
plt.title('BTC/USDT 5m RSI(14)')
plt.xlabel('Datetime')
plt.ylabel('RSI')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
