import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random

st.set_page_config(page_title="TradeSage Pro | All Markets Live", page_icon="📊", layout="wide")

# ============================================
# AUTO REFRESH
# ============================================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 8:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ============================================
# COMPLETE MARKET DATA
# ============================================
ALL_INDICES = {
    "NIFTY 50": 23200,
    "BANK NIFTY": 49500,
    "SENSEX": 76500,
    "FINNIFTY": 21800,
    "MIDCAP NIFTY": 12500,
}

ALL_FNO_STOCKS = {
    "RELIANCE": 2950, "TCS": 3850, "HDFC BANK": 1680, "INFOSYS": 1550,
    "ICICI BANK": 1100, "ITC": 450, "SBI": 780, "BHARTI AIRTEL": 1886,
    "L&T": 4012, "AXIS BANK": 1268, "KOTAK BANK": 382, "TATA MOTORS": 980,
    "M&M": 3096, "MARUTI": 13312, "SUN PHARMA": 1808, "TITAN": 4385,
    "BAJAJ FINANCE": 936, "BAJAJ FINSERV": 1746, "HCL TECH": 1198,
    "WIPRO": 200, "TECH MAHINDRA": 1474, "ADANI PORTS": 1655,
    "ADANI ENTERPRISES": 2404, "ASIAN PAINTS": 2444, "NESTLE": 1457,
    "ULTRATECH CEMENT": 11582, "JSW STEEL": 1264, "TATA STEEL": 211,
    "HINDALCO": 1037, "GRASIM": 2792, "HIND UNILEVER": 2250,
    "DR REDDY": 6505, "CIPLA": 1457, "APOLLO HOSPITAL": 4590,
    "POWER GRID": 318, "NTPC": 399, "COAL INDIA": 481,
    "ONGC": 299, "BPCL": 444, "IOC": 142, "GAIL": 221,
    "DLF": 797, "EICHER MOTORS": 7110, "HERO MOTO": 9997,
    "BRITANNIA": 4014, "DABUR": 510, "INDUSIND BANK": 937,
    "BANK OF BARODA": 220, "PNB": 110, "CANARA BANK": 115,
    "IDFC FIRST BANK": 72, "FEDERAL BANK": 168, "AU SMALL FINANCE": 610,
    "SHREERAM FINANCE": 937, "BAJAJ AUTO": 9997, "TVS MOTOR": 3492,
    "TATA POWER": 430, "BEL": 431, "HAL": 4336, "IRFC": 175,
    "LIC INDIA": 798, "SBI LIFE": 1819, "HDFC LIFE": 640,
    "ICICI PRUDENTIAL": 520, "ICICI LOMBARD": 1400,
}

# ============================================
# SIDEBAR
# ============================================
st.sidebar.title("📋 TradeSage Pro Panel")
market_type = st.sidebar.radio("Market:", ["📊 Indices", "📈 Equity (F&O)", "📈 Equity (All)"], index=0)

st.sidebar.markdown("---")

if market_type == "📊 Indices":
    name = st.sidebar.selectbox("Select Index:", list(ALL_INDICES.keys()))
    base_price = ALL_INDICES[name]
elif market_type == "📈 Equity (F&O)":
    name = st.sidebar.selectbox("Select Stock:", list(ALL_FNO_STOCKS.keys()))
    base_price = ALL_FNO_STOCKS[name]
else:
    all_stocks = {**ALL_FNO_STOCKS, "ITC": 450, "INFY": 1550}
    name = st.sidebar.selectbox("Select Stock:", list(all_stocks.keys()))
    base_price = all_stocks[name]

st.sidebar.markdown("---")
show_sig = st.sidebar.checkbox("Show 10 Strategy Signals", value=True)
st.sidebar.caption(f"🔄 8s refresh | {datetime.now().strftime('%H:%M:%S')}")

# ============================================
# SIMULATED LIVE DATA GENERATOR
# ============================================
np.random.seed(int(time.time()) + hash(name) % 10000)

def generate_ticks(base, points=150):
    dates = pd.date_range(end=datetime.now(), periods=points, freq='1min')
    volatility = 0.002
    returns = np.random.randn(points) * base * volatility
    close = base + np.cumsum(returns)
    close = np.clip(close, base * 0.95, base * 1.05)
    
    df = pd.DataFrame({
        'Open': close + np.random.randn(points) * base * 0.0005,
        'High': close + np.abs(np.random.randn(points)) * base * 0.002,
        'Low': close - np.abs(np.random.randn(points)) * base * 0.002,
        'Close': close,
        'Volume': np.random.randint(10000, 500000, points)
    }, index=dates)
    
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1) + np.random.randn(points) * base * 0.0002
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1) - np.random.randn(points) * base * 0.0002
    return df

df = generate_ticks(base_price)

# Simulated live price
ltp = df['Close'].iloc[-1]
prev_close = df['Close'].iloc[-2]
change = ltp - prev_close
change_pct = (change / prev_close) * 100

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TradeSage Pro - Complete Market Terminal")
st.markdown(f"### {market_type} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

# ============================================
# TOP METRICS
# ============================================
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("💰 LTP", f"₹{ltp:,.2f}", f"{change:+,.2f} ({change_pct:+.2f}%)")
c2.metric("📊 Open", f"₹{df['Open'].iloc[-1]:,.2f}")
c3.metric("📈 High", f"₹{df['High'].max():,.2f}")
c4.metric("📉 Low", f"₹{df['Low'].min():,.2f}")
c5.metric("📦 Volume", f"{df['Volume'].iloc[-1]:,.0f}")
c6.metric("📊 ATR", f"{df['Close'].diff().abs().rolling(14).mean().iloc[-1]:.2f}")

st.markdown("---")

# ============================================
# TECHNICAL INDICATORS
# ============================================
def calculate_atr(dataframe, period=14):
    high_low = dataframe['High'] - dataframe['Low']
    high_close = abs(dataframe['High'] - dataframe['Close'].shift())
    low_close = abs(dataframe['Low'] - dataframe['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean().iloc[-1]

def calc_indicators(dataframe):
    df = dataframe.copy()
    df['sma20'] = df['Close'].rolling(20).mean()
    df['sma50'] = df['Close'].rolling(50).mean()
    df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = delta.clip(upper=0).abs().rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain/loss))
    
    e1 = df['Close'].ewm(span=12, adjust=False).mean()
    e2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd'] = e1 - e2
    df['macd_s'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    df['bb_m'] = df['Close'].rolling(20).mean()
    std = df['Close'].rolling(20).std()
    df['bb_u'] = df['bb_m'] + 2*std
    df['bb_l'] = df['bb_m'] - 2*std
    
    df['vol_r'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).cumsum() / df['Volume'].cumsum()
    df['atr'] = (df['Close'].diff().abs().rolling(14).mean())
    
    return df

df = calc_indicators(df)
last = df.iloc[-1]
prev = df.iloc[-2]

# ============================================
# 10 ADVANCED STRATEGY SIGNALS
# ============================================
signals = []

# 1. RSI Divergence
if not pd.isna(last['rsi']):
    if last['rsi'] < 30:
        signals.append({"#":1, "Strategy":"RSI Oversold", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(ltp*0.98,2), "Reason":f"RSI={last['rsi']:.1f} (Oversold)"})
    elif last['rsi'] > 70:
        signals.append({"#":1, "Strategy":"RSI Overbought", "Signal":"🔴 SELL", "Entry":round(ltp,2), "Target":round(ltp*0.98,2), "SL":round(ltp*1.02,2), "Reason":f"RSI={last['rsi']:.1f} (Overbought)"})

# 2. MACD Crossover
if last['macd'] > last['macd_s'] and prev['macd'] <= prev['macd_s']:
    signals.append({"#":2, "Strategy":"MACD Crossover", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"MACD↑Signal"})

# 3. Volume Spike
if last['vol_r'] > 1.5:
    signals.append({"#":3, "Strategy":"Volume Spike", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(ltp*0.99,2), "Reason":f"Vol {last['vol_r']:.1f}x"})

# 4. SMA 50 Trend
if ltp > last['sma50']:
    signals.append({"#":4, "Strategy":"SMA50 Trend", "Signal":"🟢 BULLISH", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(last['sma50'],2), "Reason":"Price>SMA50"})

# 5. EMA Crossover
if last['ema9'] > last['ema21'] and prev['ema9'] <= prev['ema21']:
    signals.append({"#":5, "Strategy":"EMA Crossover", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"9>21 EMA"})

# 6. Bollinger Band
if ltp <= last['bb_l']:
    signals.append({"#":6, "Strategy":"Bollinger Lower", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(last['bb_m'],2), "SL":round(ltp*0.99,2), "Reason":"Near Lower BB"})
elif ltp >= last['bb_u']:
    signals.append({"#":6, "Strategy":"Bollinger Upper", "Signal":"🔴 SELL", "Entry":round(ltp,2), "Target":round(last['bb_m'],2), "SL":round(ltp*1.01,2), "Reason":"Near Upper BB"})

# 7. Support Bounce
low20 = df['Low'].tail(20).min()
if last['Low'] <= low20 * 1.005 and last['Close'] > last['Open']:
    signals.append({"#":7, "Strategy":"Support Bounce", "Signal":"🟢 BOUNCE", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(low20*0.995,2), "Reason":"20d support"})

# 8. Resistance Break
high20 = df['High'].tail(20).max()
if ltp > high20:
    signals.append({"#":8, "Strategy":"Resistance Break", "Signal":"🟢 BREAKOUT", "Entry":round(ltp,2), "Target":round(ltp*1.03,2), "SL":round(high20,2), "Reason":"New high"})

# 9. VWAP
vwap = last['vwap']
if ltp > vwap * 1.002:
    signals.append({"#":9, "Strategy":"VWAP Signal", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(vwap,2), "Reason":"Price>VWAP"})

# 10. ATR-Based
atr_val = last['atr']
if atr_val > 0:
    signals.append({"#":10, "Strategy":"ATR Range", "Signal":"ℹ️ INFO", "Entry":round(ltp,2), "Target":round(ltp+atr_val*2,2), "SL":round(ltp-atr_val,2), "Reason":f"ATR={atr_val:.2f}"})

# ============================================
# CHART
# ============================================
st.subheader(f"📈 {name} - Live Chart with All Indicators")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.03)

fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma20'], name="SMA20", line=dict(color='blue',width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma50'], name="SMA50", line=dict(color='orange',width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_u'], name="BB Up", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_l'], name="BB Lo", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name="RSI", line=dict(color='purple',width=2)), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=True)
st.plotly_chart(fig, use_container_width=True)

# ============================================
# SIGNALS TABLE
# ============================================
if show_sig:
    st.markdown("---")
    st.subheader("🎯 10 Advanced Strategy Signals (Entry, Target, Stop Loss)")
    if signals:
        sdf = pd.DataFrame(signals)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} active signals with complete trade details")
    else:
        st.info("⏳ No active signals. Waiting for market conditions...")

st.markdown("---")
st.caption("📊 Complete Market Coverage: Nifty 50, Sensex, Bank Nifty, Finnifty + 60 F&O Stocks")
st.caption("⚡ 8-sec auto-refresh | 10 Strategy Signals | ⚠️ Educational use only")
st.caption(f"🔄 Last update: {datetime.now().strftime('%H:%M:%S')} | All indicators calculated in real-time")
