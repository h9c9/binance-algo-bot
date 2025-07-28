import ccxt
import pandas as pd
import numpy as np
import json

class BinanceWeightedAlgoTrader:
    def __init__(self, api_key, secret, symbols=None, timeframes=None, risk_per_trade=0.01, config_path="adaptive_config.json"):
        self.api_key = api_key
        self.secret = secret
        self.symbols = symbols or ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
        self.timeframes = timeframes or ["5m", "15m", "1h", "4h", "1d"]
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })
        self.risk_per_trade = risk_per_trade
        self.last_signals = {s: None for s in self.symbols}
        with open(config_path, "r") as f:
            self.adaptive_config = json.load(f)

    def get_usdt_balance(self):
        balance = self.exchange.fetch_balance()
        usdt = balance['total']['USDT']
        return usdt

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        data = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def calculate_indicators(self, df, cfg):
        # Fallback to defaults if not present
        ema_fast_len = cfg.get('ema_fast', 8)
        ema_slow_len = cfg.get('ema_slow', 21)
        rsi_period = cfg.get('rsi_length', 14)
        vol_window = cfg.get('volume_window', 20)
        df['ema_fast'] = df['close'].ewm(span=ema_fast_len).mean()
        df['ema_slow'] = df['close'].ewm(span=ema_slow_len).mean()
        df['rsi'] = self.rsi(df['close'], rsi_period)
        df['vwap'] = self.vwap(df)
        df['vol_z'] = (df['volume'] - df['volume'].rolling(vol_window).mean()) / df['volume'].rolling(vol_window).std()
        return df

    def rsi(self, series, period):
        delta = series.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=period).mean()
        avg_loss = pd.Series(loss).rolling(window=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def vwap(self, df):
        return (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

    def score_signal(self, df, cfg):
        score = 0
        last = df.iloc[-1]
        w = cfg.get('weights', {})
        # Use safe get for every config param
        ema_w = w.get('ema', 1)
        rsi_w = w.get('rsi', 1)
        vwap_w = w.get('vwap', 1)
        volume_w = w.get('volume', 1)

        # EMA cross
        if last['ema_fast'] > last['ema_slow']:
            score += ema_w
        else:
            score -= ema_w

        # RSI logic
        rsi_oversold = cfg.get('rsi_oversold', 30)
        rsi_overbought = cfg.get('rsi_overbought', 70)
        if last['rsi'] < rsi_oversold:
            score += rsi_w
        elif last['rsi'] > rsi_overbought:
            score -= rsi_w

        # VWAP logic
        if last['close'] > last['vwap']:
            score += vwap_w
        else:
            score -= vwap_w

        # Volume spike
        vol_zscore = cfg.get('volume_zscore', 1.5)
        if last['vol_z'] > vol_zscore:
            score += volume_w

        # You can add more indicators below (adx, mean reversion etc.)

        return score

    def multi_tf_analysis(self, symbol):
        # ---- 1. Macro Sentiment Filter (4H & 1D) ----
        macro_timeframes = ["4h", "1d"]
        macro_sentiment = []
        for tf in macro_timeframes:
            cfg = self.adaptive_config[symbol][tf]
            df = self.fetch_ohlcv(symbol, tf)
            df = self.calculate_indicators(df, cfg)
            score = self.score_signal(df, cfg)
            macro_sentiment.append(score)
        # Sentiment threshold can be tuned; here we want both to agree (both bullish or bearish)
        macro_bias = "bullish" if all(s > 0 for s in macro_sentiment) else "bearish" if all(
            s < 0 for s in macro_sentiment) else "neutral"

        if macro_bias == "neutral":
            return "avoid", 0  # Don't trade if regime isn't clear

        # ---- 2. Trend Confirmation (1H & 15M) ----
        trend_timeframes = ["1h", "15m"]
        trend_signals = []
        for tf in trend_timeframes:
            cfg = self.adaptive_config[symbol][tf]
            df = self.fetch_ohlcv(symbol, tf)
            df = self.calculate_indicators(df, cfg)
            score = self.score_signal(df, cfg)
            trend_signals.append(score)
        # Confirm trend aligns with macro bias
        trend_ok = all((s > 0 if macro_bias == "bullish" else s < 0) for s in trend_signals)

        if not trend_ok:
            return "avoid", 0  # Only trade if trend confirms macro bias

        # ---- 3. Entry/Exit Signal (15M & 5M) ----
        execution_timeframes = ["15m", "5m"]
        exec_scores = []
        for tf in execution_timeframes:
            cfg = self.adaptive_config[symbol][tf]
            df = self.fetch_ohlcv(symbol, tf)
            df = self.calculate_indicators(df, cfg)
            score = self.score_signal(df, cfg)
            exec_scores.append(score)

        # For entry, require both 15m and 5m to trigger in same direction
        if macro_bias == "bullish" and all(s > 1 for s in exec_scores):
            return "buy", np.mean(exec_scores)
        elif macro_bias == "bearish" and all(s < -1 for s in exec_scores):
            return "sell", np.mean(exec_scores)
        else:
            return "avoid", np.mean(exec_scores)

    def get_position_size(self, symbol):
        balance = self.exchange.fetch_balance()
        usdt = balance['total']['USDT']
        risk = usdt * self.risk_per_trade
        ticker = self.exchange.fetch_ticker(symbol)
        price = ticker['last']
        size = risk / price
        return size

    def execute_trade(self, symbol, side, stoploss_perc=0.01, trailing_perc=0.005):
        amount = self.get_position_size(symbol)
        ticker = self.exchange.fetch_ticker(symbol)
        price = ticker['last']
        if side == "buy":
            order = self.exchange.create_market_buy_order(symbol, amount)
            stoploss = price * (1 - stoploss_perc)
            self.place_stoploss(symbol, "sell", amount, stoploss, trailing_perc)
            print(f"BUY {symbol} at {price:.2f} | Stoploss: {stoploss:.2f}")
        elif side == "sell":
            order = self.exchange.create_market_sell_order(symbol, amount)
            stoploss = price * (1 + stoploss_perc)
            self.place_stoploss(symbol, "buy", amount, stoploss, trailing_perc)
            print(f"SELL {symbol} at {price:.2f} | Stoploss: {stoploss:.2f}")
        return order

    def place_stoploss(self, symbol, side, amount, stop_price, trailing_perc):
        params = {
            "stopPrice": round(stop_price, 2),
            "type": "STOP_MARKET",
        }
        try:
            self.exchange.create_order(symbol, "STOP_MARKET", side, amount, None, params)
            print(f"Placed stoploss for {symbol} at {stop_price:.2f}")
        except Exception as e:
            print(f"Stoploss error: {e}")

    def run(self):
        print("Starting weighted multi-symbol trading...")
        for symbol in self.symbols:
            try:
                signal, score = self.multi_tf_analysis(symbol)
                print(f"{symbol} | Signal: {signal.upper()} | Score: {score:.2f}")
                if signal in ["buy", "sell"] and self.last_signals[symbol] != signal:
                    self.execute_trade(symbol, signal)
                    self.last_signals[symbol] = signal
                else:
                    print(f"{symbol}: No action.")
            except Exception as e:
                print(f"{symbol}: Error: {e}")
