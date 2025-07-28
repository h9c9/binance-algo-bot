import streamlit as st
from streamlit_autorefresh import st_autorefresh
from binance_weighted_algo import BinanceWeightedAlgoTrader

API_KEY = "wQO0PGPi9yLWoLwg0ETK4TM7Qy7AxZ3f4eEfE3B8AzT5yDZtTVZRevC4XO3EK44l"
SECRET_KEY ="vQdSmkkGhbK2oozLFyDER0x0kla5CpR63Fg2INftD2OlhIR7NcOkiJBD1k9r8Das"

# Auto-refresh every 30 seconds
st_autorefresh(interval=30 * 1000, key="auto_refresh")

# Initialize the bot
bot = BinanceWeightedAlgoTrader(API_KEY, SECRET_KEY)

# ---- Dashboard layout ----
st.set_page_config(page_title="Binance Weighted Algo Dashboard", layout="wide")
st.title("🚦 Binance Weighted Algo Dashboard")

# Fetch and show account balance
try:
    usdt_balance = bot.get_usdt_balance()
    st.sidebar.header("Account Info")
    st.sidebar.metric("USDT Balance", f"${usdt_balance:,.2f}" if usdt_balance else "Error")
except Exception as e:
    st.sidebar.header("Account Info")
    st.sidebar.metric("USDT Balance", "Error")

st.header("Live Signals & Trade Details")

table_data = []

for symbol in bot.symbols:
    try:
        signal, score = bot.multi_tf_analysis(symbol)
        last_trade = bot.last_signals.get(symbol, "N/A")
        trade_status = "OPEN" if signal in ["buy", "sell"] else "No Action"
        table_data.append({
            "Symbol": symbol,
            "Signal": signal.upper(),
            "Score": f"{score:.2f}",
            "Last Trade": last_trade.upper() if last_trade else "N/A",
            "Status": trade_status
        })
    except Exception as e:
        table_data.append({
            "Symbol": symbol,
            "Signal": "Error",
            "Score": "-",
            "Last Trade": "N/A",
            "Status": str(e)
        })

st.table(table_data)

# Move this block BELOW the table:
with st.expander("Show Signal Generation Logic"):
    st.markdown("""
    - **EMA Fast > EMA Slow:** +1  
    - **RSI < 30 (Oversold):** +1  
    - **RSI > 70 (Overbought):** -1  
    - **VWAP (Close > VWAP):** +0.5  
    - **Volume Spike (z-score > 1.5):** +0.5  
    - <i>Timeframe weights: [5m, 15m, 1h, 4h, 1d] = [6, 5, 4, 3, 2]</i>  
    - <b>Buy if score > 2 and at least 3 TFs bullish</b>  
    - <b>Sell if score < -2 and at least 3 TFs bearish</b>  
    - <b>Otherwise, Avoid</b>
    """, unsafe_allow_html=True)

st.info("Dashboard auto-refreshes every 30 seconds. You can also manually rerun (Ctrl+R or click Rerun).")

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

st.header("Batch Backtest Heatmap & Results")

# Load batch results
results = pd.read_csv("batch_backtest_results.csv")

# Make a pivot table for heatmap (symbols as rows, timeframes as columns)
heatmap_data = results.pivot(index="symbol", columns="timeframe", values="net_return")

# Draw heatmap using Seaborn/Matplotlib
fig, ax = plt.subplots(figsize=(8, 3))
sns.heatmap(heatmap_data, annot=True, fmt=".0f", center=0, cmap="RdYlGn", ax=ax)
plt.title("Net Return by Symbol/Timeframe")

st.pyplot(fig)

# Also show results as a sortable table
st.subheader("Full Batch Results Table")
st.dataframe(results.sort_values(["net_return"], ascending=False), use_container_width=True)
