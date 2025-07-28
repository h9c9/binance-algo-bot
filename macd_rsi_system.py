import pandas as pd
import matplotlib.pyplot as plt

# ---- SETTINGS ----
filename = ('sol_usdt_ohlcv_1m.csv')  # Change for any symbol/timeframe

# MACD params
fast = 12
slow = 26
signal = 9

# RSI params
rsi_period = 14
rsi_overbought = 70
rsi_oversold = 30

# ---- LOAD DATA ----
df = pd.read_csv(filename)

# ---- INDICATORS ----

# MACD
df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
df['macd'] = df['ema_fast'] - df['ema_slow']
df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# ---- SIGNAL LOGIC ----
# Buy: MACD crosses above Signal AND RSI < 30
# Sell: MACD crosses below Signal AND RSI > 70

df['signal'] = 0
df.loc[
    (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)) & (df['rsi'] < rsi_oversold),
    'signal'
] = 1
df.loc[
    (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)) & (df['rsi'] > rsi_overbought),
    'signal'
] = -1

# ---- BACKTEST: Plotting signals ----
plt.figure(figsize=(15, 7))
plt.plot(df['datetime'], df['close'], label='Close Price')
plt.scatter(df[df['signal'] == 1]['datetime'], df[df['signal'] == 1]['close'], marker='^', color='g', label='Buy Signal', s=100)
plt.scatter(df[df['signal'] == -1]['datetime'], df[df['signal'] == -1]['close'], marker='v', color='r', label='Sell Signal', s=100)
plt.title('Price with MACD/RSI Buy/Sell Signals')
plt.legend()
plt.grid(True)
plt.show()

# ---- Plot MACD and RSI ----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True)
# MACD
ax1.plot(df['datetime'], df['macd'], label='MACD', color='b')
ax1.plot(df['datetime'], df['macd_signal'], label='Signal Line', color='orange')
ax1.legend()
ax1.set_title('MACD')

# RSI
ax2.plot(df['datetime'], df['rsi'], label='RSI', color='purple')
ax2.axhline(rsi_overbought, color='red', linestyle='--', label='Overbought')
ax2.axhline(rsi_oversold, color='green', linestyle='--', label='Oversold')
ax2.legend()
ax2.set_title('RSI')
plt.show()

# ---- Simple Stats ----
n_buys = (df['signal'] == 1).sum()
n_sells = (df['signal'] == -1).sum()
print(f"Number of Buy signals: {n_buys}")
print(f"Number of Sell signals: {n_sells}")

# ... (previous code to calculate signals)

# ------------- SIMPLE BACKTEST -------------
trades = []
position = 0  # 0 = flat, 1 = long
entry_price = 0
entry_time = None

for i, row in df.iterrows():
    if position == 0 and row['signal'] == 1:
        # Open long position
        position = 1
        entry_price = row['close']
        entry_time = row['datetime']
    elif position == 1 and row['signal'] == -1:
        # Close long position
        exit_price = row['close']
        exit_time = row['datetime']
        trades.append({
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'pnl': exit_price - entry_price
        })
        position = 0

# If we end with an open position, close at the last available price
if position == 1:
    exit_price = df.iloc[-1]['close']
    exit_time = df.iloc[-1]['datetime']
    trades.append({
        'entry_time': entry_time,
        'entry_price': entry_price,
        'exit_time': exit_time,
        'exit_price': exit_price,
        'pnl': exit_price - entry_price
    })

# Create a DataFrame of trades
trades_df = pd.DataFrame(trades)

if not trades_df.empty:
    total_pnl = trades_df['pnl'].sum()
    win_trades = (trades_df['pnl'] > 0).sum()
    loss_trades = (trades_df['pnl'] <= 0).sum()
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if win_trades > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] <= 0]['pnl'].mean() if loss_trades > 0 else 0

    print(f"\nBacktest Results:")
    print(f"Total trades: {len(trades_df)}")
    print(f"Wins: {win_trades} | Losses: {loss_trades}")
    print(f"Total PnL: {total_pnl:.2f}")
    print(f"Average Win: {avg_win:.2f} | Average Loss: {avg_loss:.2f}")

    print("\nSample trades:")
    print(trades_df.tail(5))
else:
    print("No completed trades for backtest.")


    def advanced_backtest(
            df,
            stop_loss_perc=0.01,  # 1% stop loss (change as needed)
            trailing_stop_perc=None,  # Set e.g. 0.01 for 1% trailing, or None to disable
            trade_size=1.0,  # Number of "contracts" or coins per trade
            allow_short=True,  # Enable/disable short trades
            commission_perc=0.0005  # 0.05% per trade
    ):
        trades = []
        position = 0  # 0 = flat, 1 = long, -1 = short
        entry_price = 0
        entry_time = None
        trailing_stop = None

        for i, row in df.iterrows():
            close = row['close']
            signal = row['signal']

            # -- Entry logic --
            if position == 0:
                if signal == 1:
                    # Open long
                    position = 1
                    entry_price = close
                    entry_time = row['datetime']
                    trailing_stop = entry_price * (1 - trailing_stop_perc) if trailing_stop_perc else None
                elif allow_short and signal == -1:
                    # Open short
                    position = -1
                    entry_price = close
                    entry_time = row['datetime']
                    trailing_stop = entry_price * (1 + trailing_stop_perc) if trailing_stop_perc else None

            # -- Position management --
            elif position == 1:
                # Check stop loss
                if close <= entry_price * (1 - stop_loss_perc):
                    exit_reason = 'Stop Loss'
                    exit_price = entry_price * (1 - stop_loss_perc)
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'LONG',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'pnl': (exit_price - entry_price) * trade_size - commission_perc * (
                                    entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None
                # Check trailing stop
                elif trailing_stop_perc:
                    new_trailing = close * (1 - trailing_stop_perc)
                    if new_trailing > trailing_stop:
                        trailing_stop = new_trailing
                    if close <= trailing_stop:
                        exit_reason = 'Trailing Stop'
                        exit_price = close
                        exit_time = row['datetime']
                        trades.append({
                            'side': 'LONG',
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'exit_time': exit_time,
                            'exit_price': exit_price,
                            'reason': exit_reason,
                            'pnl': (exit_price - entry_price) * trade_size - commission_perc * (
                                        entry_price + exit_price) * trade_size
                        })
                        position = 0
                        entry_price = 0
                        trailing_stop = None
                # Check sell signal
                elif signal == -1:
                    exit_reason = 'Sell Signal'
                    exit_price = close
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'LONG',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'pnl': (exit_price - entry_price) * trade_size - commission_perc * (
                                    entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None

            elif position == -1 and allow_short:
                # Check stop loss
                if close >= entry_price * (1 + stop_loss_perc):
                    exit_reason = 'Stop Loss'
                    exit_price = entry_price * (1 + stop_loss_perc)
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'SHORT',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'pnl': (entry_price - exit_price) * trade_size - commission_perc * (
                                    entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None
                # Check trailing stop
                elif trailing_stop_perc:
                    new_trailing = close * (1 + trailing_stop_perc)
                    if new_trailing < trailing_stop:
                        trailing_stop = new_trailing
                    if close >= trailing_stop:
                        exit_reason = 'Trailing Stop'
                        exit_price = close
                        exit_time = row['datetime']
                        trades.append({
                            'side': 'SHORT',
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'exit_time': exit_time,
                            'exit_price': exit_price,
                            'reason': exit_reason,
                            'pnl': (entry_price - exit_price) * trade_size - commission_perc * (
                                        entry_price + exit_price) * trade_size
                        })
                        position = 0
                        entry_price = 0
                        trailing_stop = None
                # Check buy signal (exit short)
                elif signal == 1:
                    exit_reason = 'Buy Signal'
                    exit_price = close
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'SHORT',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'pnl': (entry_price - exit_price) * trade_size - commission_perc * (
                                    entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None

        # Final open position close
        if position != 0:
            exit_reason = 'Final Exit'
            exit_price = df.iloc[-1]['close']
            exit_time = df.iloc[-1]['datetime']
            pnl = (exit_price - entry_price) * trade_size if position == 1 else (entry_price - exit_price) * trade_size
            pnl -= commission_perc * (entry_price + exit_price) * trade_size
            trades.append({
                'side': 'LONG' if position == 1 else 'SHORT',
                'entry_time': entry_time,
                'entry_price': entry_price,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'reason': exit_reason,
                'pnl': pnl
            })

        return pd.DataFrame(trades)


    # Example usage (you can change parameters as needed)
    results = advanced_backtest(
        df,
        stop_loss_perc=0.01,  # 1% stop
        trailing_stop_perc=0.02,  # 2% trailing (or None)
        trade_size=1.0,  # Each trade = 1 coin
        allow_short=True,  # Enable shorts
        commission_perc=0.0005  # 0.05% commission per trade leg
    )

    # Print stats and some trades
    if not results.empty:
        total_pnl = results['pnl'].sum()
        win_trades = (results['pnl'] > 0).sum()
        loss_trades = (results['pnl'] <= 0).sum()
        avg_win = results[results['pnl'] > 0]['pnl'].mean() if win_trades > 0 else 0
        avg_loss = results[results['pnl'] <= 0]['pnl'].mean() if loss_trades > 0 else 0

        print(f"\nAdvanced Backtest Results:")
        print(f"Total trades: {len(results)}")
        print(f"Wins: {win_trades} | Losses: {loss_trades}")
        print(f"Total PnL: {total_pnl:.2f}")
        print(f"Average Win: {avg_win:.2f} | Average Loss: {avg_loss:.2f}")
        print("\nSample trades:")
        print(results.tail(5))
    else:
        print("No completed trades for backtest.")


