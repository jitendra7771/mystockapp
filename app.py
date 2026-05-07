import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

st.set_page_config(page_title="TradeSage Pro | NSE Live", page_icon="📊", layout="wide")

# ============================================
# AUTO REFRESH (5 सेकंड)
# ============================================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ============================================
# SIDEBAR
# ============================================
st.sidebar.title("📋 TradeSage Pro Panel")
market_type = st.sidebar.radio("Market:", ["📈 Equity", "📊 Index", "🔄 F&O"], index=1)

symbol = "NSEI.NS"
name = "NIFTY 50"

if market_type == "📊 Index":
    index_map = {"NIFTY 50": "NSEI.NS", "BANK NIFTY": "BANKNIFTY.NS", "SENSEX": "SENSEX.BO"}
    name = st.sidebar.selectbox("Index:", list(index_map.keys()))
    symbol = index_map[name]

elif market_type == "📈 Equity":
    equity_map = {"RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC BANK": "HDFCBANK.NS", "INFOSYS": "INFY.NS", "ICICI BANK": "ICICIBANK.NS", "ITC": "ITC.NS", "SBI": "SBIN.NS", "TATA MOTORS": "TATAMOTORS.NS"}
    name = st.sidebar.selectbox("Stock:", list(equity_map.keys()))
    symbol = equity_map[name]

else:
    fno_map = {"NIFTY": "NSEI.NS", "BANKNIFTY": "BANKNIFTY.NS"}
    name = st.sidebar.selectbox("F&O:", list(fno_map.keys()))
    symbol = fno_map[name]

st.sidebar.markdown("---")
show_sig = st.sidebar.checkbox("Show Strategy Signals", value=True)
st.sidebar.caption(f"🔄 5s refresh | {datetime.now().strftime('%H:%M:%S')}")

# ============================================
# FETCH DATA
# ============================================
@st.cache_data(ttl=5)
def get_data(sym):
    ticker = yf.Ticker(sym)
    df = ticker.history(period="5d", interval="5m")
    return df

df = get_data(symbol)

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TradeSage Pro - NSE Live Terminal")
st.markdown(f"### {market_type} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if df.empty:
    st.warning("⚠️ Market closed or data unavailable. Try during market hours (9:15 AM - 3:30 PM, Mon-Fri)")
    st.info("Showing last available data if any...")
    st.stop()

last = df.iloc[-1]
ltp = last['Close']
prev_close = df.iloc[-2]['Close'] if len(df) > 1 else ltp
change = ltp - prev_close
change_pct = (change / prev_close) * 100

# ============================================
# TOP METRICS
# ============================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 LTP", f"₹{ltp:,.2f}", f"{change:+,.2f} ({change_pct:+.2f}%)")
c2.metric("📊 Open", f"₹{last['Open']:,.2f}")
c3.metric("📈 High", f"₹{df['High'].max():,.2f}")
c4.metric("📉 Low", f"₹{df['Low'].min():,.2f}")
c5.metric("📦 Volume", f"{last['Volume']:,.0f}")

st.markdown("---")

# ============================================
# INDICATORS
# ============================================
def calculate_indicators(dataframe):
    df = dataframe.copy()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = delta.clip(upper=0).abs().rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain / loss))
    df['sma20'] = df['Close'].rolling(20).mean()
    df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd'] = e1 - e2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['bb_mid'] = df['Close'].rolling(20).mean()
    std = df['Close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2 * std
    df['bb_low'] = df['bb_mid'] - 2 * std
    df['vol_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    return df

df = calculate_indicators(df)
last = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else last

# ============================================
# 10 STRATEGY SIGNALS
# ============================================
signals = []

# 1. RSI Oversold
if not pd.isna(last['rsi']):
    if last['rsi'] < 30:
        signals.append({"Strategy": "1. RSI Oversold", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.02,2), "SL": round(ltp*0.98,2), "Reason": f"RSI={last['rsi']:.1f} (Oversold)"})
    elif last['rsi'] > 70:
        signals.append({"Strategy": "1. RSI Overbought", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(ltp*0.98,2), "SL": round(ltp*1.02,2), "Reason": f"RSI={last['rsi']:.1f} (Overbought)"})

# 2. MACD Crossover
if last['macd'] > last['macd_signal'] and prev['macd'] <= prev['macd_signal']:
    signals.append({"Strategy": "2. MACD Crossover", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.015,2), "SL": round(ltp*0.99,2), "Reason": "MACD crossed above Signal"})
elif last['macd'] < last['macd_signal'] and prev['macd'] >= prev['macd_signal']:
    signals.append({"Strategy": "2. MACD Crossover", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(ltp*0.985,2), "SL": round(ltp*1.01,2), "Reason": "MACD crossed below Signal"})

# 3. Volume Spike
if last['vol_ratio'] > 1.5:
    signals.append({"Strategy": "3. Volume Spike", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.02,2), "SL": round(ltp*0.99,2), "Reason": f"Volume {last['vol_ratio']:.1f}x avg"})

# 4. SMA 20 Trend
if ltp > last['sma20']:
    signals.append({"Strategy": "4. SMA 20 Trend", "Signal": "🟢 BULLISH", "Entry": round(ltp,2), "Target": round(ltp*1.02,2), "SL": round(last['sma20'],2), "Reason": "Price above 20 SMA"})

# 5. EMA Crossover
if last['ema9'] > last['ema21'] and prev['ema9'] <= prev['ema21']:
    signals.append({"Strategy": "5. EMA Crossover", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.015,2), "SL": round(ltp*0.99,2), "Reason": "9 EMA crossed above 21 EMA"})

# 6. Bollinger Band
if ltp <= last['bb_low']:
    signals.append({"Strategy": "6. Bollinger Lower", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(last['bb_mid'],2), "SL": round(ltp*0.99,2), "Reason": "Price near Lower Band"})
elif ltp >= last['bb_up']:
    signals.append({"Strategy": "6. Bollinger Upper", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(last['bb_mid'],2), "SL": round(ltp*1.01,2), "Reason": "Price near Upper Band"})

# 7. Support Bounce (20-period Low)
low_20 = df['Low'].tail(20).min()
if last['Low'] <= low_20 * 1.005 and last['Close'] > last['Open']:
    signals.append({"Strategy": "7. Support Bounce", "Signal": "🟢 BOUNCE", "Entry": round(ltp,2), "Target": round(ltp*1.02,2), "SL": round(low_20*0.995,2), "Reason": "Bouncing from 20-period low"})

# 8. Resistance Break
high_20 = df['High'].tail(20).max()
if ltp > high_20:
    signals.append({"Strategy": "8. Resistance Break", "Signal": "🟢 BREAKOUT", "Entry": round(ltp,2), "Target": round(ltp*1.03,2), "SL": round(high_20,2), "Reason": "Broke 20-period high"})

# 9. VWAP Signal
df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
vwap = df['vwap'].iloc[-1]
if ltp > vwap * 1.002:
    signals.append({"Strategy": "9. VWAP Buy", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.015,2), "SL": round(vwap,2), "Reason": "Price > VWAP"})
elif ltp < vwap * 0.998:
    signals.append({"Strategy": "9. VWAP Sell", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(vwap,2), "SL": round(ltp*1.01,2), "Reason": "Price < VWAP"})

# 10. RSI Divergence (Simple)
rsi_now = last['rsi']
rsi_prev = df['rsi'].iloc[-5] if len(df) > 5 else rsi_now
price_now = ltp
price_prev = df['Close'].iloc[-5] if len(df) > 5 else price_now
if price_now > price_prev and rsi_now < rsi_prev:
    signals.append({"Strategy": "10. RSI Divergence", "Signal": "🔴 WEAK", "Entry": round(ltp,2), "Target": round(ltp*0.98,2), "SL": round(ltp*1.01,2), "Reason": "Bearish Divergence"})

# ============================================
# CHART
# ============================================
st.subheader(f"📈 {name} - Live Chart")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma20'], name="SMA 20", line=dict(color='blue', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_up'], name="BB Upper", line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_low'], name="BB Lower", line=dict(color='gray', width=1, dash='dot')), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name="RSI", line=dict(color='purple', width=2)), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.update_layout(height=500, showlegend=True, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# ============================================
# SIGNALS TABLE
# ============================================
if show_sig:
    st.markdown("---")
    st.subheader("🎯 10 Strategy Signals (Live)")
    if signals:
        sdf = pd.DataFrame(signals)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} active signals with Entry, Target & Stop Loss")
    else:
        st.info("⏳ No active signals right now. Waiting for market conditions...")

st.markdown("---")
st.caption("📡 Data: NSE via Yahoo Finance | 5-sec auto-refresh | ⚠️ Educational use only")
st.caption(f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')} | Market: 9:15 AM - 3:30 PM (Mon-Fri)")
