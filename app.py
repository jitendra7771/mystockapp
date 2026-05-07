import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import requests

st.set_page_config(page_title="TradeSage Pro | NSE Live", page_icon="📊", layout="wide")

# ============================================
# AUTO REFRESH (10 सेकंड - Rate limit से बचने के लिए)
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

symbol = "NIFTY 50"
name = "NIFTY 50"
ltp = 0

st.sidebar.markdown("---")

if market_type == "📊 Index":
    index_map = {"NIFTY 50": "NIFTY 50", "BANK NIFTY": "BANK NIFTY", "SENSEX": "SENSEX"}
    name = st.sidebar.selectbox("Index:", list(index_map.keys()))
    symbol = index_map[name]
else:
    equity_map = {"RELIANCE": "RELIANCE", "TCS": "TCS", "HDFC BANK": "HDFCBANK", "INFOSYS": "INFY", "ICICI BANK": "ICICIBANK", "ITC": "ITC", "SBI": "SBIN", "TATA MOTORS": "TATAMOTORS"}
    name = st.sidebar.selectbox("Stock:", list(equity_map.keys()))
    symbol = equity_map[name]

st.sidebar.markdown("---")
show_sig = st.sidebar.checkbox("Show Strategy Signals", value=True)
st.sidebar.caption(f"🔄 10s refresh | {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.caption("📡 Data: NSE Official")

# ============================================
# FETCH LIVE NSE DATA
# ============================================
@st.cache_data(ttl=10)
def fetch_nse_data(sym):
    try:
        url = f"https://www.nseindia.com/api/quote-equity?symbol={sym}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        resp = session.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            price = data.get('priceInfo', {})
            return {
                'ltp': price.get('lastPrice', 0),
                'open': price.get('open', 0),
                'high': price.get('intraDayHighLow', {}).get('max', 0),
                'low': price.get('intraDayHighLow', {}).get('min', 0),
                'prev_close': price.get('previousClose', 0),
                'volume': price.get('totalTradedVolume', 0),
                'change': price.get('change', 0),
                'pChange': price.get('pChange', 0)
            }
    except:
        pass
    return {'ltp': 0, 'open': 0, 'high': 0, 'low': 0, 'prev_close': 0, 'volume': 0, 'change': 0, 'pChange': 0}

# For indices, use a simpler API
@st.cache_data(ttl=10)
def fetch_index_data(sym):
    try:
        if sym == "NIFTY 50":
            key = "NIFTY"
        elif sym == "BANK NIFTY":
            key = "BANKNIFTY"
        else:
            key = "SENSEX"
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={key}"
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        resp = session.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            item = data.get('data', [{}])[0]
            return {
                'ltp': item.get('lastPrice', 0),
                'open': item.get('open', 0),
                'high': item.get('high', 0),
                'low': item.get('low', 0),
                'prev_close': item.get('previousClose', 0),
                'volume': item.get('totalTradedVolume', 0),
                'change': item.get('change', 0),
                'pChange': item.get('pChange', 0)
            }
    except:
        pass
    return {'ltp': 0, 'open': 0, 'high': 0, 'low': 0, 'prev_close': 0, 'volume': 0, 'change': 0, 'pChange': 0}

if market_type == "📊 Index":
    data = fetch_index_data(symbol)
else:
    data = fetch_nse_data(symbol)

ltp = data.get('ltp', 0)

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 TradeSage Pro - NSE Live Terminal")
st.markdown(f"### {market_type} | {name} | {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")

if ltp <= 0:
    st.warning("⚠️ Market closed or data unavailable. Try during market hours (9:15 AM - 3:30 PM, Mon-Fri)")
    st.stop()

# ============================================
# TOP METRICS
# ============================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 LTP", f"₹{ltp:,.2f}", f"{data['change']:+,.2f} ({data['pChange']:+.2f}%)")
c2.metric("📊 Open", f"₹{data['open']:,.2f}")
c3.metric("📈 High", f"₹{data['high']:,.2f}")
c4.metric("📉 Low", f"₹{data['low']:,.2f}")
c5.metric("📦 Volume", f"{data['volume']:,.0f}")

st.markdown("---")

# ============================================
# SAMPLE SIGNALS (NSE डेटा से)
# ============================================
st.subheader("🎯 Strategy Signals")

# Simple signals based on available data
signals = []
if data['change'] > 0 and data['pChange'] > 0.5:
    signals.append({"Strategy": "1. Momentum", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(ltp*1.01,2), "SL": round(ltp*0.995,2), "Reason": f"+{data['pChange']:.2f}% up"})
elif data['change'] < 0 and data['pChange'] < -0.5:
    signals.append({"Strategy": "1. Momentum", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(ltp*0.99,2), "SL": round(ltp*1.005,2), "Reason": f"{data['pChange']:.2f}% down"})

if ltp > data['open']:
    signals.append({"Strategy": "2. Open Breakout", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(data['high']*1.005,2), "SL": round(data['open'],2), "Reason": "Above Open"})
else:
    signals.append({"Strategy": "2. Open Breakdown", "Signal": "🔴 SELL", "Entry": round(ltp,2), "Target": round(data['low']*0.995,2), "SL": round(data['open'],2), "Reason": "Below Open"})

if ltp > (data['high'] + data['low']) / 2:
    signals.append({"Strategy": "3. Range Break", "Signal": "🟢 BUY", "Entry": round(ltp,2), "Target": round(data['high'],2), "SL": round((data['high']+data['low'])/2,2), "Reason": "Above mid-range"})

if data['volume'] > 1000000:
    signals.append({"Strategy": "4. High Volume", "Signal": "🟢 ACTIVE", "Entry": round(ltp,2), "Target": round(ltp*1.02,2), "SL": round(ltp*0.99,2), "Reason": f"Vol: {data['volume']:,.0f}"})

# Sample chart (simple line)
chart_data = pd.DataFrame({
    'Price': [data['open'], ltp, data['high'], data['low'], data['prev_close']],
    'Label': ['Open', 'LTP', 'High', 'Low', 'Prev Close']
})

st.bar_chart(chart_data.set_index('Label'))

if show_sig:
    st.markdown("---")
    if signals:
        sdf = pd.DataFrame(signals)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.success(f"✅ {len(signals)} signals active with Entry, Target & Stop Loss")
    else:
        st.info("⏳ Waiting for signals...")

st.markdown("---")
st.caption("📡 Data: NSE Official Website | 10-sec refresh | ⚠️ Educational use only")
st.caption(f"🔄 Last update: {datetime.now().strftime('%H:%M:%S')} | Market: 9:15 AM - 3:30 PM")
