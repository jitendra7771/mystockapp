import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import json

st.set_page_config(page_title="TradeSage Pro | NSE Live", page_icon="📊", layout="wide")

# ============================================
# AUTO REFRESH
# ============================================
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 10:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ============================================
# SIDEBAR
# ============================================
st.sidebar.title("📋 TradeSage Pro Panel")
market_type = st.sidebar.radio("Market:", ["📈 Equity", "📊 Index"], index=1)

index_map = {"NIFTY 50": "NIFTY 50", "BANK NIFTY": "BANK NIFTY"}
equity_map = {"RELIANCE": "RELIANCE", "TCS": "TCS", "HDFC BANK": "HDFCBANK", "INFOSYS": "INFY", "ICICI BANK": "ICICIBANK", "ITC": "ITC", "SBI": "SBIN", "TATA MOTORS": "TATAMOTORS"}

if market_type == "📊 Index":
    name = st.sidebar.selectbox("Index:", list(index_map.keys()))
    symbol = index_map[name]
else:
    name = st.sidebar.selectbox("Stock:", list(equity_map.keys()))
    symbol = equity_map[name]

st.sidebar.markdown("---")
show_sig = st.sidebar.checkbox("Show 10 Strategy Signals", value=True)
st.sidebar.caption(f"🔄 10s auto-refresh | {datetime.now().strftime('%H:%M:%S')}")

# ============================================
# NSE DATA FETCH
# ============================================
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

@st.cache_data(ttl=10)
def fetch_nse_live(sym, is_index):
    try:
        session.get("https://www.nseindia.com", timeout=5)
        if is_index:
            key = "NIFTY" if sym == "NIFTY 50" else "BANKNIFTY"
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={key}"
            resp = session.get(url, timeout=5)
            if resp.status_code == 200:
                d = resp.json().get('data', [{}])[0]
                return {'ltp': d.get('lastPrice',0), 'open': d.get('open',0), 'high': d.get('high',0), 'low': d.get('low',0), 'prev': d.get('previousClose',0), 'vol': d.get('totalTradedVolume',0), 'chg': d.get('change',0), 'chgp': d.get('pChange',0)}
        else:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={sym}"
            resp = session.get(url, timeout=5)
            if resp.status_code == 200:
                p = resp.json().get('priceInfo', {})
                return {'ltp': p.get('lastPrice',0), 'open': p.get('open',0), 'high': p.get('intraDayHighLow',{}).get('max',0), 'low': p.get('intraDayHighLow',{}).get('min',0), 'prev': p.get('previousClose',0), 'vol': p.get('totalTradedVolume',0), 'chg': p.get('change',0), 'chgp': p.get('pChange',0)}
    except:
        pass
    return {'ltp':0, 'open':0, 'high':0, 'low':0, 'prev':0, 'vol':0, 'chg':0, 'chgp':0}

@st.cache_data(ttl=60)
def fetch_nse_history(sym, is_index):
    try:
        end = datetime.now()
        start = end - timedelta(days=30)
        if is_index:
            key = "NIFTY" if sym == "NIFTY 50" else "BANKNIFTY"
            url = f"https://www.nseindia.com/api/historical/indicesHistory?indexType={key.lower()}&from={start.strftime('%d-%m-%Y')}&to={end.strftime('%d-%m-%Y')}"
        else:
            url = f"https://www.nseindia.com/api/historical/cm/equity?symbol={sym}&from={start.strftime('%d-%m-%Y')}&to={end.strftime('%d-%m-%Y')}"
        session.get("https://www.nseindia.com", timeout=5)
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            records = resp.json().get('data', [])
            df = pd.DataFrame(records)
            if not df.empty:
                cols = {'CH_TIMESTAMP': 'Date', 'CH_OPENING_PRICE': 'Open', 'CH_TRADE_HIGH_PRICE': 'High', 'CH_TRADE_LOW_PRICE': 'Low', 'CH_CLOSING_PRICE': 'Close', 'CH_TOT_TRADED_QTY': 'Volume'}
                df.rename(columns={k:v for k,v in cols.items() if k in df.columns}, inplace=True)
                for c in ['Open','High','Low','Close','Volume']:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                df = df.dropna(subset=['Close'])
                return df
    except:
        pass
    return pd.DataFrame()

is_idx = market_type == "📊 Index"
live = fetch_nse_live(symbol, is_idx)
hist = fetch_nse_history(symbol, is_idx)
ltp = live.get('ltp', 0)

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TradeSage Pro - NSE Live Terminal")
st.markdown(f"### {market_type} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if ltp <= 0:
    st.warning("⚠️ Market closed. Try Mon-Fri 9:15 AM - 3:30 PM")
    st.stop()

# ============================================
# TOP METRICS
# ============================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 LTP", f"₹{ltp:,.2f}", f"{live['chg']:+,.2f} ({live['chgp']:+.2f}%)")
c2.metric("📊 Open", f"₹{live['open']:,.2f}")
c3.metric("📈 High", f"₹{live['high']:,.2f}")
c4.metric("📉 Low", f"₹{live['low']:,.2f}")
c5.metric("📦 Volume", f"{live['vol']:,.0f}")

st.markdown("---")

# ============================================
# TECHNICAL INDICATORS
# ============================================
def calc_indicators(df):
    if len(df) < 20:
        return df
    df['sma20'] = df['Close'].rolling(20).mean()
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
    return df

signals = []

if not hist.empty:
    hist = calc_indicators(hist)
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else last

    # 1. RSI
    if not pd.isna(last.get('rsi', np.nan)):
        if last['rsi'] < 30:
            signals.append({"#":1, "Strategy":"RSI Oversold", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(ltp*1.02,2), "SL":round(ltp*0.98,2), "Reason":f"RSI={last['rsi']:.1f}"})
        elif last['rsi'] > 70:
            signals.append({"#":1, "Strategy":"RSI Overbought", "Signal":"🔴 SELL", "Entry":ltp, "Target":round(ltp*0.98,2), "SL":round(ltp*1.02,2), "Reason":f"RSI={last['rsi']:.1f}"})

    # 2. MACD
    if last['macd'] > last['macd_s'] and prev['macd'] <= prev['macd_s']:
        signals.append({"#":2, "Strategy":"MACD Crossover", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"MACD↑Signal"})

    # 3. Volume Spike
    if last.get('vol_r', 1) > 1.5:
        signals.append({"#":3, "Strategy":"Volume Spike", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(ltp*1.02,2), "SL":round(ltp*0.99,2), "Reason":f"Vol {last['vol_r']:.1f}x"})

    # 4. SMA Trend
    if ltp > last.get('sma20', ltp):
        signals.append({"#":4, "Strategy":"SMA20 Trend", "Signal":"🟢 BULLISH", "Entry":ltp, "Target":round(ltp*1.02,2), "SL":round(last['sma20'],2), "Reason":"Price > SMA20"})

    # 5. EMA Crossover
    if last['ema9'] > last['ema21'] and prev['ema9'] <= prev['ema21']:
        signals.append({"#":5, "Strategy":"EMA Crossover", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(ltp*1.015,2), "SL":round(ltp*0.99,2), "Reason":"9>21 EMA"})

    # 6. Bollinger
    if ltp <= last.get('bb_l', ltp):
        signals.append({"#":6, "Strategy":"Bollinger Lower", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(last['bb_m'],2), "SL":round(ltp*0.99,2), "Reason":"Near Lower BB"})
    elif ltp >= last.get('bb_u', ltp):
        signals.append({"#":6, "Strategy":"Bollinger Upper", "Signal":"🔴 SELL", "Entry":ltp, "Target":round(last['bb_m'],2), "SL":round(ltp*1.01,2), "Reason":"Near Upper BB"})

    # 7. Support
    low20 = hist['Low'].tail(20).min()
    if live['low'] <= low20 * 1.005 and ltp > live['open']:
        signals.append({"#":7, "Strategy":"Support Bounce", "Signal":"🟢 BOUNCE", "Entry":ltp, "Target":round(ltp*1.02,2), "SL":round(low20*0.995,2), "Reason":"20-day support"})

    # 8. Resistance
    high20 = hist['High'].tail(20).max()
    if ltp > high20:
        signals.append({"#":8, "Strategy":"Resistance Break", "Signal":"🟢 BREAKOUT", "Entry":ltp, "Target":round(ltp*1.03,2), "SL":round(high20,2), "Reason":"New 20d high"})

    # 9. VWAP
    vwap = last.get('vwap', ltp)
    if ltp > vwap * 1.002:
        signals.append({"#":9, "Strategy":"VWAP Signal", "Signal":"🟢 BUY", "Entry":ltp, "Target":round(ltp*1.015,2), "SL":round(vwap,2), "Reason":"Price > VWAP"})

    # 10. Mid Range
    mid = (live['high'] + live['low']) / 2
    if ltp > mid:
        signals.append({"#":10, "Strategy":"Day Range", "Signal":"🟢 STRONG", "Entry":ltp, "Target":live['high'], "SL":round(mid,2), "Reason":"Above day mid"})

# ============================================
# CHART
# ============================================
if not hist.empty and len(hist) >= 5:
    st.subheader(f"📈 {name} - Chart with Indicators")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="OHLC"), row=1, col=1)
    if 'sma20' in hist.columns:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['sma20'], name="SMA20", line=dict(color='blue',width=1)), row=1, col=1)
    if 'bb_u' in hist.columns:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['bb_u'], name="BB Up", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['bb_l'], name="BB Lo", line=dict(color='gray',width=1,dash='dot')), row=1, col=1)
    if 'rsi' in hist.columns:
        fig.add_trace(go.Scatter(x=hist.index, y=hist['rsi'], name="RSI", line=dict(color='purple',width=2)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# SIGNALS TABLE
# ============================================
if show_sig:
    st.markdown("---")
    st.subheader("🎯 10 Strategy Signals (Entry, Target, Stop Loss)")
    if signals:
        sdf = pd.DataFrame(signals)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} active signals")
    else:
        st.info("⏳ No signals. Waiting for market conditions...")

st.markdown("---")
st.caption("📡 Live Data: NSE Official | Historical Data: NSE | 10-sec refresh | ⚠️ Educational use only")
st.caption(f"🔄 Last update: {datetime.now().strftime('%H:%M:%S')}")
