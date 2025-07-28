import pandas as pd
import json
from binance_weighted_algo import BinanceWeightedAlgoTrader

class Backtester:
    def __init__(self, config_path, symbol, timeframe, initial_balance=1000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        with open(config_path, "r") as f:
            self.config = json.load(f)
        self.cfg = self.config[symbol][timeframe]
        self.bt = BinanceWeightedAlgoTrader(
            api_key="",
            secret="",
            symbols=[symbol],
            timeframes=[timeframe],
            config_path=config_path
        )

    def load_data(self, filename):
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def run(self, data: pd.DataFrame, print_trades=True):
        balance = self.initial_balance
        position = 0
        entry_price = 0
        trades = []
        last_signal = "none"
        df = self.bt.calculate_indicators(data.copy(), self.cfg)
        for i in range(50, len(df)):
            row = df.iloc[:i+1]
            # Use multi_tf_analysis for realistic signal
            signal, score = self.bt.multi_tf_analysis(self.symbol)
            price = row.iloc[-1]['close']

            # Enter trade
            if position == 0 and signal in ["buy", "sell"] and signal != last_signal:
                position = 1 if signal == "buy" else -1
                entry_price = price
                trades.append({"entry_time": row.iloc[-1]['timestamp'], "entry_price": entry_price, "side": signal})
                if print_trades:
                    print(f"{signal.upper()} at {price:.2f} on {row.iloc[-1]['timestamp']}")
            # Exit trade (opposite signal or hit SL/TP)
            if position != 0:
                stoploss = entry_price * (1 - self.cfg["strategy"]["stoploss"] if position == 1 else 1 + self.cfg["strategy"]["stoploss"])
                takeprofit = entry_price * (1 + self.cfg["strategy"]["takeprofit"] if position == 1 else 1 - self.cfg["strategy"]["takeprofit"])
                if (position == 1 and (price <= stoploss or price >= takeprofit or signal == "sell")) or \
                   (position == -1 and (price >= stoploss or price <= takeprofit or signal == "buy")):
                    pnl = (price - entry_price) * position
                    balance += pnl
                    trades[-1].update({
                        "exit_time": row.iloc[-1]['timestamp'],
                        "exit_price": price,
                        "pnl": pnl
                    })
                    if print_trades:
                        print(f"EXIT at {price:.2f} on {row.iloc[-1]['timestamp']} | PnL: {pnl:.2f} | Balance: {balance:.2f}")
                    position = 0
                    entry_price = 0
            last_signal = signal

        # Results summary
        trades_df = pd.DataFrame(trades)
        print(f"\nBacktest finished: {len(trades)} trades | Final Balance: {balance:.2f} | Net Return: {balance - self.initial_balance:.2f}")
        if not trades_df.empty:
            print(trades_df.tail())
        return trades_df, balance

# USAGE
if __name__ == "__main__":
    # --- Change as needed ---
    symbol = "SOL/USDT"
    timeframe = "1h"
    ohlcv_csv = "SOLUSDT_1h.csv"
    config_path = "adaptive_config.json"

    backtester = Backtester(config_path, symbol, timeframe, initial_balance=1000)
    data = backtester.load_data(ohlcv_csv)
    backtester.run(data)
