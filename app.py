import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import requests
import json

st.set_page_config(page_title="TradeSage Pro | Upstox Live", page_icon="📊", layout="wide")

# ============================================
# UPSTOX CREDENTIALS
# ============================================
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2MDY2MDEiLCJqdGkiOiI2OWZjOTNlYmVhYmNiMTA1YWVhYzQ2ZmEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaXNFeHRlbmRlZCI6dHJ1ZSwiaWF0IjoxNzc4MTYwNjE5LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE4MDk3MjcyMDB9.xIVEXstq39A1xI1MlJ5Dby3wzToHs1WJcw8LdSZebGU"
BASE_URL = "https://api.upstox.com/v2"

# ============================================
# AUTO REFRESH (हर 3 सेकंड)
# ============================================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 3:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ============================================
# SIDEBAR
# ============================================
st.sidebar.title("📋 TradeSage Pro Panel")
st.sidebar.markdown("---")

market_type = st.sidebar.radio("Market:", ["📈 Equity", "📊 Index", "🔄 F&O"], index=1)

# Symbols mapping (Upstox format)
index_map = {
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "BANK NIFTY": "NSE_INDEX|Nifty Bank",
    "SENSEX": "BSE_INDEX|SENSEX",
}

equity_map = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFC BANK": "NSE_EQ|INE040A01034",
    "INFOSYS": "NSE_EQ|INE009A01021",
    "ICICI BANK": "NSE_EQ|INE090A01021",
    "ITC": "NSE_EQ|INE154A01025",
    "SBI": "NSE_EQ|INE062A01020",
    "TATA MOTORS": "NSE_EQ|INE155A01022",
}

st.sidebar.markdown("---")

if market_type == "📊 Index":
    symbol_name = st.sidebar.selectbox("Select Index:", list(index_map.keys()))
    instrument_key = index_map[symbol_name]
elif market_type == "📈 Equity":
    symbol_name = st.sidebar.selectbox("Select Stock:", list(equity_map.keys()))
    instrument_key = equity_map[symbol_name]
else:
    symbol_name = st.sidebar.selectbox("F&O:", ["NIFTY", "BANKNIFTY"])
    instrument_key = index_map.get(f"{symbol_name} 50" if symbol_name == "NIFTY" else "BANK NIFTY", "NSE_INDEX|Nifty 50")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Strategies")
show_strategies = st.sidebar.checkbox("Show Strategy Signals", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(f"🔄 Auto-refresh: 3s | {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.caption("📡 Data: Upstox Official API")

# ============================================
# DATA FETCH FROM UPSTOX
# ============================================
@st.cache_data(ttl=3)
def fetch_ltp(token, key):
    try:
        url = f"{BASE_URL}/market-data/ltp"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {"instrument_key": key}
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        return {}
    except:
        return {}

@st.cache_data(ttl=3)
def fetch_ohlc(token, key):
    try:
        url = f"{BASE_URL}/market-data/ohlc"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        params = {"instrument_key": key, "interval": "1minute"}
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        return {}
    except:
        return {}

ltp_data = fetch_ltp(ACCESS_TOKEN, instrument_key)
ohlc_data = fetch_ohlc(ACCESS_TOKEN, instrument_key)

# ============================================
# PROCESS DATA
# ============================================
current_price = ltp_data.get(instrument_key, {}).get('last_price', 0)

# Build DataFrame from OHLC
if ohlc_data and 'candles' in ohlc_data:
    candles = ohlc_data['candles']
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
else:
    df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

# ============================================
# INDICATORS & STRATEGIES
# ============================================
def calculate_all(df, current_price):
    signals = []
    if df.empty or len(df) < 5:
        return signals
    
    df['sma_20'] = df['close'].rolling(20).mean()
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    df['bb_mid'] = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2*std
    df['bb_low'] = df['bb_mid'] - 2*std
    
    df['vol_sma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_sma']
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    # 1. RSI
    if not pd.isna(last.get('rsi', np.nan)):
        if last['rsi'] < 30:
            signals.append({"Strategy": "RSI Oversold", "Signal": "🟢 BUY", "Entry": current_price, "Target": round(current_price*1.02,2), "SL": round(current_price*0.98,2), "Reason": f"RSI={last['rsi']:.1f}"})
        elif last['rsi'] > 70:
            signals.append({"Strategy": "RSI Overbought", "Signal": "🔴 SELL", "Entry": current_price, "Target": round(current_price*0.98,2), "SL": round(current_price*1.02,2), "Reason": f"RSI={last['rsi']:.1f}"})
    
    # 2. MACD
    if last.get('macd', 0) > last.get('macd_signal', 0) and prev.get('macd', 0) <= prev.get('macd_signal', 0):
        signals.append({"Strategy": "MACD Crossover", "Signal": "🟢 BUY", "Entry": current_price, "Target": round(current_price*1.015,2), "SL": round(current_price*0.99,2), "Reason": "MACD ↑ Signal"})
    
    # 3. Volume Spike
    if last.get('vol_ratio', 1) > 1.5:
        signals.append({"Strategy": "Volume Spike", "Signal": "🟢 BUY", "Entry": current_price, "Target": round(current_price*1.02,2), "SL": round(current_price*0.99,2), "Reason": f"Vol {last['vol_ratio']:.1f}x"})
    
    # 4. SMA Trend
    if current_price > last.get('sma_20', current_price):
        signals.append({"Strategy": "SMA Trend", "Signal": "🟢 BULLISH", "Entry": current_price, "Target": round(current_price*1.02,2), "SL": round(last['sma_20'],2), "Reason": "Price > 20 SMA"})
    
    # 5. EMA Crossover
    if last.get('ema_9', 0) > last.get('ema_21', 0):
        signals.append({"Strategy": "EMA Crossover", "Signal": "🟢 BUY", "Entry": current_price, "Target": round(current_price*1.015,2), "SL": round(current_price*0.99,2), "Reason": "9 EMA > 21 EMA"})
    
    # 6. Bollinger
    if current_price <= last.get('bb_low', current_price):
        signals.append({"Strategy": "Bollinger Band", "Signal": "🟢 BUY", "Entry": current_price, "Target": round(last.get('bb_mid', current_price),2), "SL": round(current_price*0.99,2), "Reason": "Near Lower Band"})
    elif current_price >= last.get('bb_up', current_price):
        signals.append({"Strategy": "Bollinger Band", "Signal": "🔴 SELL", "Entry": current_price, "Target": round(last.get('bb_mid', current_price),2), "SL": round(current_price*1.01,2), "Reason": "Near Upper Band"})
    
    return signals

signals = calculate_all(df, current_price) if current_price > 0 else []

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TradeSage Pro - Upstox Live Terminal")
st.markdown(f"### {market_type} | {symbol_name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if current_price <= 0:
    st.warning("⚠️ Market closed or data unavailable. Try during market hours (9:15 AM - 3:30 PM)")
    st.stop()

# ============================================
# TOP METRICS
# ============================================
col1, col2, col3, col4, col5 = st.columns(5)

change_data = ltp_data.get(instrument_key, {})
change = change_data.get('change', 0)
change_pct = change_data.get('change_percent', 0)

with col1:
    st.metric("💰 LTP", f"₹{current_price:,.2f}", f"{change:+,.2f} ({change_pct:+.2f}%)")

with col2:
    if not df.empty:
        st.metric("📊 Open", f"₹{df['open'].iloc[-1]:,.2f}")

with col3:
    if not df.empty:
        st.metric("📈 High", f"₹{df['high'].max():,.2f}")

with col4:
    if not df.empty:
        st.metric("📉 Low", f"₹{df['low'].min():,.2f}")

with col5:
    if not df.empty:
        st.metric("📦 Volume", f"{df['volume'].iloc[-1]:,.0f}")

st.markdown("---")

# ============================================
# CHART
# ============================================
if not df.empty:
    st.subheader(f"📈 {symbol_name} - Live Chart")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="OHLC"), row=1, col=1)
    
    if 'sma_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_20'], name="SMA 20", line=dict(color='blue', width=1)), row=1, col=1)
    
    if 'rsi' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name="RSI", line=dict(color='purple', width=2)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    fig.update_layout(height=550, showlegend=True, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# STRATEGY SIGNALS
# ============================================
if show_strategies:
    st.markdown("---")
    st.subheader("🎯 Strategy Signals (Real-Time)")
    
    if signals:
        sdf = pd.DataFrame(signals)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} active signals | Entry/Exit, Target & Stop Loss above")
    else:
        st.info("No active signals right now. Waiting for market conditions...")

st.markdown("---")
st.caption("⚠️ Educational purpose only | 📡 Data: Upstox Official API | 3-sec auto-refresh")
st.caption(f"🔄 Last update: {datetime.now().strftime('%H:%M:%S')} | Market hours: 9:15 AM - 3:30 PM")
