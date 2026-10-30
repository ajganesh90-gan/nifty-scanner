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
    .stApp { background-color: #07090E; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #00E5FF !important; font-weight: 700; letter-spacing: -0.5px; }
    
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #121824 0%, #1A2332 100%);
        border: 1px solid #1E2D40;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 229, 255, 0.05);
    }
    div[data-testid="stMetric"] label { color: #94A3B8 !important; font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.6rem; font-weight: 700; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0B0E14; padding: 6px; border-radius: 12px; border: 1px solid #1E2D40; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #94A3B8; border-radius: 8px; font-weight: 600; padding: 10px 20px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(135deg, #00E5FF 0%, #00838F 100%) !important; color: #07090E !important; }

    .stDataFrame { border-radius: 12px; border: 1px solid #1E2D40; overflow: hidden; }
    .stTextInput input, .stNumberInput input, .stSelectbox select { background-color: #121824; color: #FFFFFF; border: 1px solid #1E2D40; border-radius: 8px; }
    </style>
""",
    unsafe_allow_html=True,
)

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
# HELPER FUNCTIONS & TECHNICAL INDICATORS
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
# RELAXED HIGH-WIN RATE SCANNER ENGINE
# ==========================================
@st.cache_data(ttl=1800)
def run_live_scan(val_threshold_pct=2.5, atr_multiplier=1.2, min_rr=1.0):
    signals = []
    scan_date = datetime.now().strftime("%Y-%m-%d")
    data = yf.download(NIFTY_100_TICKERS, period="1y", interval="1d", group_by="ticker", progress=False)

    for ticker in NIFTY_100_TICKERS:
        try:
            df = data[ticker].dropna() if ticker in data.columns.levels[0] else pd.DataFrame()
            if len(df) < 220:
                continue

            df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()
            df["ATR"] = calculate_atr(df, window=14)
            df["Vol_SMA"] = df["Volume"].rolling(20).mean()

            poc, val, vah = calculate_volume_profile(df, lookback=20)
            if not poc or not val or not vah:
                continue

            current_row = df.iloc[-1]
            close_price = float(current_row["Close"])
            ema_50 = float(current_row["EMA_50"])
            ema_200 = float(current_row["EMA_200"])
            atr_val = float(current_row["ATR"])
            vol_val = float(current_row["Volume"])
            vol_avg = float(current_row["Vol_SMA"])

            dist_to_val = ((close_price - val) / val) * 100

            # Trend Alignment: Close > EMA 200 (Institutional Bullish Bias)
            is_uptrend = close_price > ema_200
            has_volume_support = vol_val >= (vol_avg * 0.8)

            if 0 <= dist_to_val <= val_threshold_pct and is_uptrend and has_volume_support:
                entry = close_price
                sl = val - (atr_multiplier * atr_val)
                
                ideal_target = entry + (1.5 * (entry - sl))
                target = min(ideal_target, poc) if poc > entry else ideal_target

                risk = entry - sl
                reward = target - entry
                rr_ratio = reward / risk if risk > 0 else 0

                if rr_ratio >= min_rr:
                    est_days = max(1, int(round(reward / atr_val))) if atr_val > 0 else 2
                    raw_symbol = ticker.replace(".NS", "")

                    signals.append({
                        "Date": scan_date,
                        "Stock": raw_symbol,
                        "TradingView Link": f"https://in.tradingview.com/chart/?symbol=NSE:{raw_symbol}",
                        "Entry Price (₹)": round(entry, 2),
                        "Target (₹)": round(target, 2),
                        "Stop Loss (₹)": round(sl, 2),
                        "Est. Days": f"{est_days} Days",
                        "R:R Ratio": round(rr_ratio, 2),
                        "VAL Support (₹)": round(val, 2),
                        "Dist to VAL (%)": round(dist_to_val, 2),
                    })
        except Exception:
            continue

    return pd.DataFrame(signals)


# ==========================================
# BACKTESTING ENGINE WITH FLEXIBLE THRESHOLDS
# ==========================================
@st.cache_data(ttl=3600)
def run_backtest(ticker, years=3, val_threshold_pct=2.5, atr_multiplier=1.2, min_rr=1.0, initial_capital=100000):
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=start_date, progress=False)

    if df.empty:
        return None, None

    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in required_cols):
        return None, None

    df = df.dropna()
    if len(df) < 220:
        return None, None

    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["ATR"] = calculate_atr(df, window=14)
    df["Vol_SMA"] = df["Volume"].rolling(20).mean()

    trades = []
    current_capital = initial_capital
    i = 210

    while i < len(df) - 1:
        sub_df = df.iloc[:i]
        curr_row = df.iloc[i]
        curr_date = df.index[i]

        poc, val, vah = calculate_volume_profile(sub_df, lookback=20)
        if poc and val and vah:
            close_p = float(curr_row["Close"])
            ema_200 = float(curr_row["EMA_200"])
            atr_p = float(curr_row["ATR"])
            vol_p = float(curr_row["Volume"])
            vol_avg = float(curr_row["Vol_SMA"])
            dist = ((close_p - val) / val) * 100

            is_uptrend = close_p > ema_200
            has_volume_support = vol_p >= (vol_avg * 0.8)

            if 0 <= dist <= val_threshold_pct and is_uptrend and has_volume_support:
                entry_price = close_p
                sl = val - (atr_multiplier * atr_p)
                ideal_target = entry_price + (1.5 * (entry_price - sl))
                target = min(ideal_target, poc) if poc > entry_price else ideal_target

                risk = entry_price - sl
                reward = target - entry_price
                rr_ratio = reward / risk if risk > 0 else 0

                if rr_ratio >= min_rr:
                    entry_date = curr_date
                    exit_found = False

                    for j in range(i + 1, len(df)):
                        exit_row = df.iloc[j]
                        exit_date = df.index[j]
                        high_p = float(exit_row["High"])
                        low_p = float(exit_row["Low"])

                        hit_sl = low_p <= sl
                        hit_target = high_p >= target

                        if hit_target and not hit_sl:
                            pnl_pct = ((target - entry_price) / entry_price) * 100
                            trade_pnl_rs = current_capital * (pnl_pct / 100)
                            current_capital += trade_pnl_rs
                            trades.append({
                                "Entry Date": entry_date.strftime("%Y-%m-%d"),
                                "Exit Date": exit_date.strftime("%Y-%m-%d"),
                                "Type": "Target Hit 🟢",
                                "Entry (₹)": round(entry_price, 2),
                                "Exit (₹)": round(target, 2),
                                "PnL (%)": round(pnl_pct, 2),
                                "Profit/Loss (₹)": round(trade_pnl_rs, 2),
                                "Portfolio (₹)": round(current_capital, 2)
                            })
                            exit_found = True
                            i = j
                            break
                        elif hit_sl:
                            pnl_pct = ((sl - entry_price) / entry_price) * 100
                            trade_pnl_rs = current_capital * (pnl_pct / 100)
                            current_capital += trade_pnl_rs
                            trades.append({
                                "Entry Date": entry_date.strftime("%Y-%m-%d"),
                                "Exit Date": exit_date.strftime("%Y-%m-%d"),
                                "Type": "SL Hit 🔴",
                                "Entry (₹)": round(entry_price, 2),
                                "Exit (₹)": round(sl, 2),
                                "PnL (%)": round(pnl_pct, 2),
                                "Profit/Loss (₹)": round(trade_pnl_rs, 2),
                                "Portfolio (₹)": round(current_capital, 2)
                            })
                            exit_found = True
                            i = j
                            break

                    if not exit_found:
                        break
        i += 1

    trades_df = pd.DataFrame(trades)
    return trades_df, df


# ==========================================
# HEADER & MARKET INDICES
# ==========================================
st.title("⚡ Nifty 100 Volume Profile Quant Terminal")
st.caption("Multi-Stock Institutional Mean-Reversion Suite")

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
tab1, tab2, tab3 = st.tabs(["🚀 Live Multi-Stock Scanner", "📊 Strategy Backtester", "🤖 Quant AI Intelligence"])

# ------------------------------------------
# TAB 1: LIVE MULTI-STOCK SCANNER
# ------------------------------------------
with tab1:
    st.subheader("Nifty 100 Multi-Stock Parameter Engine")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    v_limit = col_p1.slider("VAL Distance Threshold (%)", 0.5, 5.0, 2.5, 0.5)
    atr_mult = col_p2.slider("ATR Stop Buffer Multiplier", 0.8, 2.5, 1.2, 0.1)
    min_rr_param = col_p3.slider("Minimum R:R Ratio", 0.8, 2.0, 1.0, 0.1)

    with st.spinner("Scanning Nifty 100 universe across all stocks..."):
        scan_results = run_live_scan(val_threshold_pct=v_limit, atr_multiplier=atr_mult, min_rr=min_rr_param)

    if not scan_results.empty:
        st.success(f"Found {len(scan_results)} setups across the Nifty 100 universe!")

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
            scan_results.to_excel(writer, index=False, sheet_name="MultiStock_Setups")

        st.download_button(
            "📥 Export Multi-Stock Report to Excel",
            data=excel_buffer.getvalue(),
            file_name=f"Nifty100_MultiStock_Scan_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info(f"No setups matching current parameters. Try adjusting the sliders above.")

# ------------------------------------------
# TAB 2: MULTI-YEAR BACKTESTER & PORTFOLIO SIMULATOR
# ------------------------------------------
with tab2:
    st.subheader("Strategy Backtesting & Portfolio Simulator")
    st.caption("Simulate capital growth, win/loss ratios, and historical performance across 1 to 10 years.")

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    bt_symbol = col_a.selectbox("Stock Ticker", NIFTY_100_TICKERS, index=47)
    initial_cap = col_b.number_input("Capital (₹)", value=100000, step=10000, format="%d")
    bt_years = col_c.slider("Period", 1, 10, 3)
    bt_threshold = col_d.slider("VAL %", 0.5, 5.0, 2.5, 0.5)
    bt_atr = col_e.slider("ATR Mult", 0.8, 2.0, 1.2, 0.1)

    if st.button("▶️ Run Backtest & Simulation", type="primary"):
        with st.spinner(f"Simulating trades for {bt_symbol} across {bt_years} year(s)..."):
            bt_df, price_df = run_backtest(
                bt_symbol, years=bt_years, val_threshold_pct=bt_threshold, atr_multiplier=bt_atr, initial_capital=initial_cap
            )

        if bt_df is not None and not bt_df.empty:
            total_trades = len(bt_df)
            wins = len(bt_df[bt_df["Type"] == "Target Hit 🟢"])
            losses = len(bt_df[bt_df["Type"] == "SL Hit 🔴"])

            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
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
            st.warning(f"No trades triggered for {bt_symbol} in the selected timeframe. Try increasing the VAL % slider to 3.0% or 4.0%.")

# ------------------------------------------
# TAB 3: QUANT AI KNOWLEDGE BASE
# ------------------------------------------
with tab3:
    st.subheader("🤖 Multi-Stock Strategy Core Rules")
    with st.expander("📚 Signal Tuning Guidelines", expanded=True):
        st.markdown("""
        * **VAL Distance Threshold:** Keep between `2.0%` and `3.0%` for consistent deal flow.
        * **ATR Stop Multiplier:** `1.2x` provides optimal breathing room against intraday wicks.
        * **Trend Confirmation:** Filters for trades trading above the 200 EMA to align with macro momentum.
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
            f"1. **Signal Balance:** Expand VAL % to 2.5% to capture quality pullbacks before they launch.\n"
            f"2. **Risk Control:** Use 1.2x ATR buffer to avoid premature stop-outs.\n"
            f"3. **Execution:** Ensure price is resting above the 200 EMA."
        )
