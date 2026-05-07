import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

st.set_page_config(page_title="TradeSage Pro | NSE Live", page_icon="📊", layout="wide")

# AUTO REFRESH
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()

# SIDEBAR
st.sidebar.title("📋 TradeSage Pro Panel")
market_type = st.sidebar.radio("Market:", ["📈 Equity", "📊 Index", "🔄 F&O"], index=1)

index_map = {
    "NIFTY 50": "NSEI.NS",
    "BANK NIFTY": "BANKNIFTY.NS",
    "SENSEX": "SENSEX.BO",
}

equity_map = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC BANK": "HDFCBANK.NS",
    "INFOSYS": "INFY.NS", "ICICI BANK": "ICICIBANK.NS", "ITC": "ITC.NS",
    "SBI": "SBIN.NS", "TATA MOTORS": "TATAMOTORS.NS",
}

if market_type == "📊 Index":
    name = st.sidebar.selectbox("Index:", list(index_map.keys()))
    symbol = index_map[name]
elif market_type == "📈 Equity":
    name = st.sidebar.selectbox("Stock:", list(equity_map.keys()))
    symbol = equity_map[name]
else:
    name = "NIFTY 50"
    symbol = "NSEI.NS"

st.sidebar.markdown("---")
show_sig = st.sidebar.checkbox("Show Strategy Signals", value=True)
st.sidebar.caption(f"🔄 5s refresh | {datetime.now().strftime('%H:%M:%S')}")

# FETCH DATA
@st.cache_data(ttl=5)
def get_data(sym):
    t = yf.Ticker(sym)
    return t.history(period="5d", interval="5m")

df = get_data(symbol)

# MAIN
st.title("📊 TradeSage Pro - NSE Live Terminal")
st.markdown(f"### {market_type} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if df.empty:
    st.warning("⚠️ Market closed or data unavailable. Try 9:15 AM - 3:30 PM Mon-Fri")
    st.stop()

last = df.iloc[-1]
ltp = last['Close']
prev = df.iloc[-2]['Close'] if len(df) > 1 else ltp
chg = ltp - prev
chg_pct = (chg / prev) * 100

# TOP ROW
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 LTP", f"₹{ltp:,.2f}", f"{chg:+,.2f} ({chg_pct:+.2f}%)")
c2.metric("📊 Open", f"₹{last['Open']:,.2f}")
c3.metric("📈 High", f"₹{df['High'].max():,.2f}")
c4.metric("📉 Low", f"₹{df['Low'].min():,.2f}")
c5.metric("📦 Volume", f"{last['Volume']:,.0f}")

st.markdown("---")

# INDICATORS
def calc(df):
    df['rsi'] = 100 - (100 / (1 + (df['Close'].diff().clip(lower=0).rolling(14).mean() / df['Close'].diff().clip(upper=0).abs().rolling(14).mean())))
    df['sma20'] = df['Close'].rolling(20).mean()
    df['ema9'] = df['Close'].ewm(span=9).mean()
    df['ema21'] = df['Close'].ewm(span=21).mean()
    e1 = df['Close'].ewm(span=12).mean()
    e2 = df['Close'].ewm(span=26).mean()
    df['macd'] = e1 - e2
    df['macd_s'] = df['macd'].ewm(span=9).mean()
    df['bb_m'] = df['Close'].rolling(20).mean()
    s = df['Close'].rolling(20).std()
    df['bb_u'] = df['bb_m'] + 2*s
    df['bb_l'] = df['bb_m'] - 2*s
    df['vol_r'] = df['Volume'] / df['Volume'].rolling(20).mean()
    return df

df = calc(df)
last = df.iloc[-1]
prev = df.iloc[-2]

# SIGNALS
signals = []
if not pd.isna(last['rsi']):
    if last['rsi'] < 30:
        signals.append({"Strategy": "RSI Oversold", "Signal": "🟢 BUY", "Entry": ltp, "Target": round(ltp*1.02,2), "SL": round(ltp*0.98,2), "Reason": f"RSI={last['rsi']:.1f}"})
    elif last['rsi'] > 70:
        signals.append({"Strategy": "RSI Overbought", "Signal": "🔴 SELL", "Entry": ltp, "Target": round(ltp*0.98,2), "SL": round(ltp*1.02,2), "Reason": f"RSI={last['rsi']:.1f}"})
if last['macd'] > last['macd_s'] and prev['macd'] <= prev['macd_s']:
    signals.append({"Strategy": "MACD Crossover", "Signal": "🟢 BUY", "Entry": ltp, "Target": round(ltp*1.015,2), "SL": round(ltp*0.99,2), "Reason": "MACD↑Signal"})
if last['vol_r'] > 1.5:
    signals.append({"Strategy": "Volume Spike", "Signal": "🟢 BUY", "Entry": ltp, "Target": round(ltp*1.02,2), "SL": round(ltp*0.99,2), "Reason": f"Vol{last['vol_r']:.1f}x"})
if ltp > last['sma20']:
    signals.append({"Strategy": "SMA Trend", "Signal": "🟢 BULLISH", "Entry": ltp, "Target": round(ltp*1.02,2), "SL": round(last['sma20'],2), "Reason": ">20SMA"})
if last['ema9'] > last['ema21']:
    signals.append({"Strategy": "EMA Crossover", "Signal": "🟢 BUY", "Entry": ltp, "Target": round(ltp*1.015,2), "SL": round(ltp*0.99,2), "Reason": "9>21EMA"})
if ltp <= last['bb_l']:
    signals.append({"Strategy": "Bollinger", "Signal": "🟢 BUY", "Entry": ltp, "Target": round(last['bb_m'],2), "SL": round(ltp*0.99,2), "Reason": "LowBand"})

# CHART
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma20'], name="SMA20", line=dict(color='blue', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name="RSI", line=dict(color='purple', width=2)), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# SIGNALS TABLE
if show_sig:
    st.markdown("---")
    st.subheader("🎯 Strategy Signals")
    if signals:
        st.dataframe(pd.DataFrame(signals), use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} signals active")
    else:
        st.info("No signals - waiting for conditions")

st.markdown("---")
st.caption("📡 Data: NSE via Yahoo Finance | 5-sec refresh | Educational use only")
