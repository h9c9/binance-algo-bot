import pandas as pd
import matplotlib.pyplot as plt

filename = 'ohlcv_data/btc_usdt_ohlcv_5m.csv'  # Use your desired file
df = pd.read_csv(filename)

# ---- Indicators ----
# MACD
fast, slow, signal = 12, 26, 9
df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
df['macd'] = df['ema_fast'] - df['ema_slow']
df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()

# RSI
rsi_period = 14
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Block Buy/Sell
window = 20
block_threshold = 2
df['vol_mean'] = df['volume'].rolling(window).mean()
df['vol_std'] = df['volume'].rolling(window).std()
df['block_trade'] = (df['volume'] > df['vol_mean'] + block_threshold * df['vol_std'])
df['block_buy'] = df['block_trade'] & (df['close'] > df['open'])
df['block_sell'] = df['block_trade'] & (df['close'] < df['open'])

# ---- Entry Signals ----
df['long_entry'] = (
    df['block_buy'] &
    (df['macd'] > df['macd_signal']) &
    (df['macd'].shift(1) <= df['macd_signal'].shift(1)) &
    (df['rsi'] < 70)
)

df['short_entry'] = (
    df['block_sell'] &
    (df['macd'] < df['macd_signal']) &
    (df['macd'].shift(1) >= df['macd_signal'].shift(1)) &
    (df['rsi'] > 30)
)

# ---- Signal column for backtest ----
df['signal'] = 0
df.loc[df['long_entry'], 'signal'] = 1
df.loc[df['short_entry'], 'signal'] = -1

# ---- Advanced Backtest Function ----
def advanced_backtest(
    df,
    stop_loss_perc=0.01,
    trailing_stop_perc=0.02,
    trade_size=1.0,
    allow_short=True,
    commission_perc=0.0005
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
                position = 1
                entry_price = close
                entry_time = row['datetime']
                trailing_stop = entry_price * (1 - trailing_stop_perc) if trailing_stop_perc else None
            elif allow_short and signal == -1:
                position = -1
                entry_price = close
                entry_time = row['datetime']
                trailing_stop = entry_price * (1 + trailing_stop_perc) if trailing_stop_perc else None

        # -- Position management --
        elif position == 1:
            # Stop loss
            if close <= entry_price * (1 - stop_loss_perc):
                exit_price = entry_price * (1 - stop_loss_perc)
                exit_time = row['datetime']
                trades.append({
                    'side': 'LONG',
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'reason': 'Stop Loss',
                    'pnl': (exit_price - entry_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                })
                position = 0
                entry_price = 0
                trailing_stop = None
            # Trailing stop
            elif trailing_stop_perc:
                new_trailing = close * (1 - trailing_stop_perc)
                if new_trailing > trailing_stop:
                    trailing_stop = new_trailing
                if close <= trailing_stop:
                    exit_price = close
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'LONG',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': 'Trailing Stop',
                        'pnl': (exit_price - entry_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None
            # Opposite signal
            elif signal == -1:
                exit_price = close
                exit_time = row['datetime']
                trades.append({
                    'side': 'LONG',
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'reason': 'Sell Signal',
                    'pnl': (exit_price - entry_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                })
                position = 0
                entry_price = 0
                trailing_stop = None

        elif position == -1 and allow_short:
            # Stop loss
            if close >= entry_price * (1 + stop_loss_perc):
                exit_price = entry_price * (1 + stop_loss_perc)
                exit_time = row['datetime']
                trades.append({
                    'side': 'SHORT',
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'reason': 'Stop Loss',
                    'pnl': (entry_price - exit_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                })
                position = 0
                entry_price = 0
                trailing_stop = None
            # Trailing stop
            elif trailing_stop_perc:
                new_trailing = close * (1 + trailing_stop_perc)
                if new_trailing < trailing_stop:
                    trailing_stop = new_trailing
                if close >= trailing_stop:
                    exit_price = close
                    exit_time = row['datetime']
                    trades.append({
                        'side': 'SHORT',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': exit_time,
                        'exit_price': exit_price,
                        'reason': 'Trailing Stop',
                        'pnl': (entry_price - exit_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                    })
                    position = 0
                    entry_price = 0
                    trailing_stop = None
            # Opposite signal
            elif signal == 1:
                exit_price = close
                exit_time = row['datetime']
                trades.append({
                    'side': 'SHORT',
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'reason': 'Buy Signal',
                    'pnl': (entry_price - exit_price) * trade_size - commission_perc * (entry_price + exit_price) * trade_size
                })
                position = 0
                entry_price = 0
                trailing_stop = None

    # Final close
    if position != 0:
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
            'reason': 'Final Exit',
            'pnl': pnl
        })

    return pd.DataFrame(trades)

# ---- Run Advanced Backtest ----
results = advanced_backtest(
    df,
    stop_loss_perc=0.01,
    trailing_stop_perc=0.02,
    trade_size=1.0,
    allow_short=True,
    commission_perc=0.0005
)

# ---- Show Results ----
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
