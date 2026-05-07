import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

st.set_page_config(page_title="TradeSage Pro", page_icon="📊", layout="wide")

# Symbols
SYMBOLS = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC BANK": "HDFCBANK.NS",
    "INFOSYS": "INFY.NS", "ICICI BANK": "ICICIBANK.NS", "ITC": "ITC.NS",
    "SBI": "SBIN.NS", "TATA MOTORS": "TATAMOTORS.NS", "M&M": "M&M.NS",
    "MARUTI": "MARUTI.NS", "SUN PHARMA": "SUNPHARMA.NS", "TITAN": "TITAN.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS", "HCL TECH": "HCLTECH.NS", "WIPRO": "WIPRO.NS",
    "ADANI PORTS": "ADANIPORTS.NS", "ASIAN PAINTS": "ASIANPAINT.NS",
    "NESTLE": "NESTLEIND.NS", "ULTRATECH CEMENT": "ULTRATECEMCO.NS",
    "JSW STEEL": "JSWSTEEL.NS", "TATA STEEL": "TATASTEEL.NS",
    "HINDALCO": "HINDALCO.NS", "DR REDDY": "DRREDDY.NS", "CIPLA": "CIPLA.NS",
    "POWER GRID": "POWERGRID.NS", "NTPC": "NTPC.NS", "COAL INDIA": "COALINDIA.NS",
    "ONGC": "ONGC.NS", "BPCL": "BPCL.NS", "IOC": "IOC.NS",
    "DLF": "DLF.NS", "EICHER MOTORS": "EICHERMOT.NS",
    "HERO MOTO": "HEROMOTOCO.NS", "BRITANNIA": "BRITANNIA.NS",
    "HIND UNILEVER": "HINDUNILVR.NS", "LT": "LT.NS",
    "AXIS BANK": "AXISBANK.NS", "KOTAK BANK": "KOTAKBANK.NS",
}

# Sidebar
st.sidebar.title("📋 TradeSage Pro")
choice = st.sidebar.radio("Market:", ["Indices", "Stocks (F&O)"])
opts = ["NIFTY 50", "BANK NIFTY", "SENSEX"] if choice == "Indices" else [k for k in SYMBOLS if k not in ["NIFTY 50", "BANK NIFTY", "SENSEX"]]
name = st.sidebar.selectbox("Select:", opts)
sym = SYMBOLS[name]
show_sig = st.sidebar.checkbox("Show Strategy Signals", value=True)
st.sidebar.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

# Fetch Data
@st.cache_data(ttl=60)
def get_data(s):
    try:
        t = yf.Ticker(s)
        d = t.history(period="5d", interval="5m")
        return d if not d.empty else None
    except:
        return None

df = get_data(sym)

# Main Dashboard
st.title("📊 TradeSage Pro - Live Terminal")
st.markdown(f"### {choice} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if df is None or df.empty:
    st.warning("Market closed or data unavailable. Try Mon-Fri 9:15 AM - 3:30 PM")
    st.stop()

ltp = df['Close'].iloc[-1]
prev = df['Close'].iloc[-2]
chg = ltp - prev
chgp = (chg / prev) * 100

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("LTP", f"₹{ltp:,.2f}", f"{chg:+,.2f} ({chgp:+.2f}%)")
c2.metric("Open", f"₹{df['Open'].iloc[-1]:,.2f}")
c3.metric("High", f"₹{df['High'].max():,.2f}")
c4.metric("Low", f"₹{df['Low'].min():,.2f}")
c5.metric("Volume", f"{df['Volume'].iloc[-1]:,.0f}")
st.markdown("---")

# Indicators
def calc(df):
    d = df.copy()
    d['sma20'] = d['Close'].rolling(20).mean()
    d['ema9'] = d['Close'].ewm(span=9, adjust=False).mean()
    d['ema21'] = d['Close'].ewm(span=21, adjust=False).mean()
    delta = d['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = delta.clip(upper=0).abs().rolling(14).mean()
    d['rsi'] = 100 - (100 / (1 + gain/loss))
    e1 = d['Close'].ewm(span=12, adjust=False).mean()
    e2 = d['Close'].ewm(span=26, adjust=False).mean()
    d['macd'] = e1 - e2
    d['macd_s'] = d['macd'].ewm(span=9, adjust=False).mean()
    d['bb_m'] = d['Close'].rolling(20).mean()
    std = d['Close'].rolling(20).std()
    d['bb_u'] = d['bb_m'] + 2*std
    d['bb_l'] = d['bb_m'] - 2*std
    d['vol_r'] = d['Volume'] / d['Volume'].rolling(20).mean()
    return d

df = calc(df)
last = df.iloc[-1]
prevr = df.iloc[-2]

# Signals
signals = []
if not pd.isna(last['rsi']):
    if last['rsi'] < 30:
        signals.append({"#":1, "Strategy":"RSI Oversold", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(ltp*0.98,2), "Reason":f"RSI={last['rsi']:.1f}"})
    elif last['rsi'] > 70:
        signals.append({"#":1, "Strategy":"RSI Overbought", "Signal":"🔴 SELL", "Entry":round(ltp,2), "Target":round(ltp*0.98,2), "SL":round(ltp*1.02,2), "Reason":f"RSI={last['rsi']:.1f}"})
if last['macd'] > last['macd_s'] and prevr['macd'] <= prevr['macd_s']:
    signals.append({"#":2, "Strategy":"MACD Crossover", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"MACD↑Signal"})
if last['vol_r'] > 1.5:
    signals.append({"#":3, "Strategy":"Volume Spike", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(ltp*0.99,2), "Reason":f"Vol {last['vol_r']:.1f}x"})
if ltp > last['sma20']:
    signals.append({"#":4, "Strategy":"SMA20 Trend", "Signal":"🟢 BULLISH", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(last['sma20'],2), "Reason":"Price>SMA20"})
if last['ema9'] > last['ema21'] and prevr['ema9'] <= prevr['ema21']:
    signals.append({"#":5, "Strategy":"EMA Crossover", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"9>21 EMA"})
if ltp <= last['bb_l']:
    signals.append({"#":6, "Strategy":"Bollinger Lower", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(last['bb_m'],2), "SL":round(ltp*0.99,2), "Reason":"Near Lower BB"})
elif ltp >= last['bb_u']:
    signals.append({"#":6, "Strategy":"Bollinger Upper", "Signal":"🔴 SELL", "Entry":round(ltp,2), "Target":round(last['bb_m'],2), "SL":round(ltp*1.01,2), "Reason":"Near Upper BB"})
low20 = df['Low'].tail(20).min()
if last['Low'] <= low20 * 1.005 and last['Close'] > last['Open']:
    signals.append({"#":7, "Strategy":"Support Bounce", "Signal":"🟢 BOUNCE", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(low20*0.995,2), "Reason":"20d support"})
high20 = df['High'].tail(20).max()
if ltp > high20:
    signals.append({"#":8, "Strategy":"Resistance Break", "Signal":"🟢 BREAKOUT", "Entry":round(ltp,2), "Target":round(ltp*1.03,2), "SL":round(high20,2), "Reason":"New high"})
df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).cumsum() / df['Volume'].cumsum()
vwap = df['vwap'].iloc[-1]
if ltp > vwap * 1.002:
    signals.append({"#":9, "Strategy":"VWAP Signal", "Signal":"🟢 BUY", "Entry":round(ltp,2), "Target":round(ltp*1.015,2), "SL":round(vwap,2), "Reason":"Price>VWAP"})
signals.append({"#":10, "Strategy":"LTP Check", "Signal":"ℹ️ INFO", "Entry":round(ltp,2), "Target":round(ltp*1.02,2), "SL":round(ltp*0.98,2), "Reason":"Baseline"})

# Chart
st.subheader(f"📈 {name} - Live Chart")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.03)
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma20'], name="SMA20", line=dict(color='blue',width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_u'], name="BB Up", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['bb_l'], name="BB Lo", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name="RSI", line=dict(color='purple',width=2)), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# Signals Table
if show_sig:
    st.markdown("---")
    st.subheader("🎯 Strategy Signals (Entry, Target, SL)")
    if signals:
        st.dataframe(pd.DataFrame(signals), use_container_width=True, hide_index=True)
        st.success(f"{len(signals)} signals active")
    else:
        st.info("No signals")

st.markdown("---")
st.caption("Data: Yahoo Finance | Auto-refresh: 60s | Educational use only")
