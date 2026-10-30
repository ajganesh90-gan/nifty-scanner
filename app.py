from datetime import datetime, timedelta
import io
import numpy as np
import openpyxl
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ==========================================
# PAGE CONFIGURATION & FUTURISTIC STYLING
# ==========================================
st.set_page_config(
    page_title="Nifty 100 Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Global App Background & Text Contrast */
    .stApp { background-color: #07090E; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    
    /* Glowing Headers & Titles */
    h1, h2, h3 { color: #00E5FF !important; font-weight: 700; letter-spacing: -0.5px; }
    
    /* Futuristic Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #121824 0%, #1A2332 100%);
        border: 1px solid #1E2D40;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 229, 255, 0.05);
    }
    div[data-testid="stMetric"] label { color: #94A3B8 !important; font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.6rem; font-weight: 700; }

    /* Custom Styled Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0B0E14; padding: 6px; border-radius: 12px; border: 1px solid #1E2D40; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #94A3B8; border-radius: 8px; font-weight: 600; padding: 10px 20px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(135deg, #00E5FF 0%, #00838F 100%) !important; color: #07090E !important; }

    /* Dataframes & Inputs */
    .stDataFrame { border-radius: 12px; border: 1px solid #1E2D40; overflow: hidden; }
    .stTextInput input, .stNumberInput input, .stSelectbox select { background-color: #121824; color: #FFFFFF; border: 1px solid #1E2D40; border-radius: 8px; }
    </style>
""",
    unsafe_allow_html=True,
)

# Nifty 100 Tickers
NIFTY_100_TICKERS = [
    "ABB.NS", "ACC.NS", "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ADANIPOWER.NS",
    "ATGL.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "DMART.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS", "BANKBARODA.NS",
    "BERGEPAINT.NS", "BEL.NS", "BHARATFORG.NS", "BPCL.NS", "BHARTIARTL.NS", "BOSCHLTD.NS",
    "BRITANNIA.NS", "CANBK.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COLPAL.NS",
    "DLF.NS", "DABUR.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS", "GAIL.NS", "GODREJCP.NS",
    "GODREJPROP.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HAVELLS.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HAL.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ICICIGI.NS",
    "ICICIPRULI.NS", "IOC.NS", "IRCTC.NS", "IRFC.NS", "ITC.NS", "INDUSINDBK.NS", "NAUKRI.NS",
    "INFY.NS", "INDIGO.NS", "JSWSTEEL.NS", "JINDALSTEL.NS", "JIOFIN.NS", "KOTAKBANK.NS",
    "LTIM.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "MARUTI.NS", "MAXHEALTH.NS", "MSUMI.NS",
    "NTPC.NS", "NESTLEIND.NS", "ONGC.NS", "PIDILITIND.NS", "PFC.NS", "POWERGRID.NS",
    "PNB.NS", "RELIANCE.NS", "SBICARD.NS", "SBILIFE.NS", "SRF.NS", "MOTHERSON.NS", "SBIN.NS",
    "SUNPHARMA.NS", "TVSMOTOR.NS", "TCS.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS",
    "TATAPOWER.NS", "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS",
    "ULTRACEMCO.NS", "UNOMINDA.NS", "UPL.NS", "VBL.NS", "VEDL.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS",
]


# ==========================================
# HELPER FUNCTIONS & INDICATORS
# ==========================================
def calculate_atr(df, window=14):
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def calculate_volume_profile(df, lookback=20):
    window_df = df.iloc[-lookback - 1 : -1].copy()
    p_min, p_max = window_df["Low"].min(), window_df["High"].max()
    if p_min == p_max:
        return None, None, None

    bins = np.linspace(p_min, p_max, 31)
    window_df["Typical_Price"] = (window_df["High"] + window_df["Low"] + window_df["Close"]) / 3
    window_df["Bin"] = pd.cut(window_df["Typical_Price"], bins=bins, include_lowest=True)

    vp = window_df.groupby("Bin", observed=False)["Volume"].sum().reset_index()
    vp["Price_Mid"] = vp["Bin"].apply(lambda x: x.mid)

    poc_price = float(vp.loc[vp["Volume"].idxmax()]["Price_Mid"])
    total_vol = vp["Volume"].sum()

    sorted_vp = vp.sort_values(by="Volume", ascending=False)
    sorted_vp["Cum_Vol"] = sorted_vp["Volume"].cumsum()
    va_bins = sorted_vp[sorted_vp["Cum_Vol"] <= total_vol * 0.70]

    if va_bins.empty:
        return None, None, None

    val_price = float(va_bins["Price_Mid"].min())
    vah_price = float(va_bins["Price_Mid"].max())

    return poc_price, val_price, vah_price


# ==========================================
# LIVE SCANNER ENGINE
# ==========================================
@st.cache_data(ttl=1800)
def run_live_scan(val_threshold_pct=2.0, ema_period=200):
    signals = []
    scan_date = datetime.now().strftime("%Y-%m-%d")
    data = yf.download(NIFTY_100_TICKERS, period="1y", interval="1d", group_by="ticker", progress=False)

    for ticker in NIFTY_100_TICKERS:
        try:
            df = data[ticker].dropna() if ticker in data.columns.levels[0] else pd.DataFrame()
            if len(df) < ema_period + 20:
                continue

            df["EMA"] = df["Close"].ewm(span=ema_period, adjust=False).mean()
            df["ATR"] = calculate_atr(df, window=14)

            poc_price, val_price, _ = calculate_volume_profile(df, lookback=20)
            if not poc_price or not val_price:
                continue

            current_row = df.iloc[-1]
            close_price = float(current_row["Close"])
            ema_val = float(current_row["EMA"])
            atr_val = float(current_row["ATR"])

            dist_to_val = ((close_price - val_price) / val_price) * 100

            if 0 <= dist_to_val <= val_threshold_pct and close_price > ema_val:
                entry = close_price
                sl = val_price * 0.992
                target = poc_price

                if target <= entry:
                    continue

                risk = entry - sl
                reward = target - entry
                rr_ratio = reward / risk if risk > 0 else 0
                est_days = max(1, int(round(reward / atr_val))) if atr_val > 0 else 3
                raw_symbol = ticker.replace(".NS", "")

                signals.append({
                    "Date": scan_date,
                    "Stock": raw_symbol,
                    "TradingView Link": f"https://in.tradingview.com/chart/?symbol=NSE:{raw_symbol}",
                    "Entry Price (₹)": round(entry, 2),
                    "Target POC (₹)": round(target, 2),
                    "Stop Loss (₹)": round(sl, 2),
                    "Est. Days": f"{est_days} Days",
                    "R:R Ratio": round(rr_ratio, 2),
                    "200 EMA (₹)": round(ema_val, 2),
                    "VAL Support (₹)": round(val_price, 2),
                    "Dist to VAL (%)": round(dist_to_val, 2),
                })
        except Exception:
            continue

    return pd.DataFrame(signals)


# ==========================================
# BACKTESTING ENGINE WITH CAPITAL SIMULATION
# ==========================================
@st.cache_data(ttl=3600)
def run_backtest(ticker, years=3, val_threshold_pct=2.0, ema_period=200, initial_capital=100000):
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=start_date, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(ticker, axis=1, level=1) if ticker in df.columns.levels[1] else df.droplevel(1, axis=1)

    df = df.dropna()
    if len(df) < ema_period + 20:
        return None, None

    df["EMA"] = df["Close"].ewm(span=ema_period, adjust=False).mean()
    df["ATR"] = calculate_atr(df, window=14)

    trades = []
    in_trade = False
    entry_price, sl, target, entry_date = 0, 0, 0, None
    current_capital = initial_capital

    for i in range(ema_period + 20, len(df)):
        sub_df = df.iloc[:i]
        curr_row = df.iloc[i]
        curr_date = df.index[i]

        if not in_trade:
            poc, val, _ = calculate_volume_profile(sub_df, lookback=20)
            if poc and val:
                close_p = float(curr_row["Close"])
                ema_p = float(curr_row["EMA"])
                dist = ((close_p - val) / val) * 100

                if 0 <= dist <= val_threshold_pct and close_p > ema_p and poc > close_p:
                    in_trade = True
                    entry_price = close_p
                    sl = val * 0.992
                    target = poc
                    entry_date = curr_date
        else:
            high_p = float(curr_row["High"])
            low_p = float(curr_row["Low"])

            if low_p <= sl:
                pnl_pct = ((sl - entry_price) / entry_price) * 100
                trade_pnl_rs = current_capital * (pnl_pct / 100)
                current_capital += trade_pnl_rs
                trades.append({
                    "Entry Date": entry_date.strftime("%Y-%m-%d"),
                    "Exit Date": curr_date.strftime("%Y-%m-%d"),
                    "Type": "SL Hit 🔴",
                    "Entry (₹)": round(entry_price, 2),
                    "Exit (₹)": round(sl, 2),
                    "PnL (%)": round(pnl_pct, 2),
                    "Profit/Loss (₹)": round(trade_pnl_rs, 2),
                    "Portfolio (₹)": round(current_capital, 2)
                })
                in_trade = False
            elif high_p >= target:
                pnl_pct = ((target - entry_price) / entry_price) * 100
                trade_pnl_rs = current_capital * (pnl_pct / 100)
                current_capital += trade_pnl_rs
                trades.append({
                    "Entry Date": entry_date.strftime("%Y-%m-%d"),
                    "Exit Date": curr_date.strftime("%Y-%m-%d"),
                    "Type": "Target Hit 🟢",
                    "Entry (₹)": round(entry_price, 2),
                    "Exit (₹)": round(target, 2),
                    "PnL (%)": round(pnl_pct, 2),
                    "Profit/Loss (₹)": round(trade_pnl_rs, 2),
                    "Portfolio (₹)": round(current_capital, 2)
                })
                in_trade = False

    trades_df = pd.DataFrame(trades)
    return trades_df, df


# ==========================================
# HEADER & MARKET INDICES
# ==========================================
st.title("⚡ Nifty 100 Volume Profile Quant Terminal")
st.caption("Institutional Mean-Reversion Scanner & Portfolio Backtesting Suite")

try:
    indices = yf.download(["^NSEI", "^NSEBANK"], period="5d", interval="1d", progress=False)
    if not indices.empty and ("Close", "^NSEI") in indices.columns:
        n_close = float(indices[("Close", "^NSEI")].iloc[-1])
        n_prev = float(indices[("Close", "^NSEI")].iloc[-2])
        n_chg = ((n_close - n_prev) / n_prev) * 100

        b_close = float(indices[("Close", "^NSEBANK")].iloc[-1])
        b_prev = float(indices[("Close", "^NSEBANK")].iloc[-2])
        b_chg = ((b_close - b_prev) / b_prev) * 100

        c1, c2 = st.columns(2)
        c1.metric("NIFTY 50", f"₹{n_close:,.2f}", f"{n_chg:+.2f}%")
        c2.metric("BANK NIFTY", f"₹{b_close:,.2f}", f"{b_chg:+.2f}%")
except Exception:
    pass

st.divider()

# ==========================================
# TABS INTERFACE
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚀 Live Scanner", "📊 Strategy Backtester", "🤖 Quant AI Intelligence"])

# ------------------------------------------
# TAB 1: LIVE SCANNER
# ------------------------------------------
with tab1:
    st.subheader("Live Market Opportunity Scanner")
    v_limit = st.slider("VAL Distance Threshold (%)", 0.5, 5.0, 1.5, 0.5)

    with st.spinner("Scanning Nifty 100 universe for Volume Profile setups..."):
        scan_results = run_live_scan(val_threshold_pct=v_limit)

    if not scan_results.empty:
        st.success(f"Found {len(scan_results)} setups within {v_limit}% of VAL!")

        st.dataframe(
            scan_results,
            column_config={
                "TradingView Link": st.column_config.LinkColumn("TradingView Chart", display_text="📊 Open Chart")
            },
            use_container_width=True,
            hide_index=True,
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            scan_results.to_excel(writer, index=False, sheet_name="Setups")

        st.download_button(
            "📥 Export Setups to Excel",
            data=excel_buffer.getvalue(),
            file_name=f"VP_Scan_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info(f"No stocks currently sitting within {v_limit}% of VAL support. Try widening the slider to 2.5%.")

# ------------------------------------------
# TAB 2: MULTI-YEAR BACKTESTER & PORTFOLIO SIMULATOR
# ------------------------------------------
with tab2:
    st.subheader("Strategy Backtesting & Portfolio Simulator")
    st.caption("Simulate capital growth, absolute profit/loss, and historical performance over 1 to 10 years.")

    col_a, col_b, col_c, col_d = st.columns(4)
    bt_symbol = col_a.selectbox("Stock Ticker", NIFTY_100_TICKERS, index=47)
    initial_cap = col_b.number_input("Investment Amount (₹)", value=100000, step=10000, format="%d")
    bt_years = col_c.slider("Period (Years)", 1, 10, 3)
    bt_threshold = col_d.slider("VAL Threshold (%)", 0.5, 5.0, 2.0, 0.5)

    if st.button("▶️ Run Backtest & Simulation", type="primary"):
        with st.spinner(f"Simulating trades for {bt_symbol} across {bt_years} year(s)..."):
            bt_df, price_df = run_backtest(
                bt_symbol, years=bt_years, val_threshold_pct=bt_threshold, initial_capital=initial_cap
            )

        if bt_df is not None and not bt_df.empty:
            total_trades = len(bt_df)
            wins = len(bt_df[bt_df["Type"] == "Target Hit 🟢"])
            losses = len(bt_df[bt_df["Type"] == "SL Hit 🔴"])

            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            loss_rate = (losses / total_trades) * 100 if total_trades > 0 else 0
            
            final_portfolio = float(bt_df["Portfolio (₹)"].iloc[-1])
            net_profit_rs = final_portfolio - initial_cap
            total_return_pct = (net_profit_rs / initial_cap) * 100

            start_date_str = str(bt_df["Entry Date"].min())
            end_date_str = str(bt_df["Exit Date"].max())

            st.markdown("### 📈 Performance & Capital Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Initial Investment", f"₹{initial_cap:,.0f}")
            m2.metric("Final Portfolio Value", f"₹{final_portfolio:,.2f}", f"{total_return_pct:+.2f}%")
            m3.metric("Net Profit / Loss (₹)", f"₹{net_profit_rs:,.2f}")
            m4.metric("Win Rate (%)", f"{win_rate:.1f}% ({wins}W / {losses}L)")

            st.caption(f"📅 **Backtest Period:** `{start_date_str}` to `{end_date_str}` ({bt_years} Years Active Simulation)")

            # Equity Curve Plotly Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=bt_df["Exit Date"],
                y=bt_df["Portfolio (₹)"],
                mode="lines+markers",
                name="Portfolio Value",
                line=dict(color="#00E5FF", width=3),
                fill="tozeroy",
                fillcolor="rgba(0, 229, 255, 0.05)"
            ))
            fig.update_layout(
                title=f"{bt_symbol} Portfolio Growth Curve (₹{initial_cap:,} Start)",
                template="plotly_dark",
                xaxis_title="Exit Date",
                yaxis_title="Portfolio Value (₹)",
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Detailed Trade Execution Log")
            st.dataframe(bt_df, use_container_width=True, hide_index=True)
        else:
            st.warning(f"No trades triggered for {bt_symbol} in the selected timeframe. Try modifying the parameters or ticker.")

# ------------------------------------------
# TAB 3: QUANT AI KNOWLEDGE BASE
# ------------------------------------------
with tab3:
    st.subheader("🤖 Strategy Concepts & Core Rules")
    with st.expander("📚 Value Area Low (VAL) & Point of Control (POC)", expanded=True):
        st.markdown("""
        * **POC (Point of Control):** The exact price level where the highest volume was traded during the lookback period. Acts as a price magnet.
        * **VAL (Value Area Low):** The bottom institutional support boundary of the 70% volume cluster.
        * **Mean Reversion Rule:** Entering near VAL above the 200 EMA yields asymmetric risk-to-reward toward the POC target.
        """)

# ==========================================
# SIDEBAR AI QUANT ASSISTANT
# ==========================================
with st.sidebar:
    st.header("💬 Ask AI Quant Assistant")
    st.caption("Get technical answers on any stock symbol!")

    user_q = st.text_input("Enter stock or question:")
    if user_q:
        q_upper = user_q.strip().upper()
        st.write(f"**Analyzing `{q_upper}`...**")
        st.info(
            f"🤖 **Quant Insight for {q_upper}:**\n\n"
            f"1. **Trend Filter:** Confirm price is above the 200 EMA.\n"
            f"2. **Volume Profile:** Look for volume nodes clustered near VAL support.\n"
            f"3. **Execution:** Enter on bullish price action rejection with a stop loss just below VAL."
        )
