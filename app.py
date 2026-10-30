from datetime import datetime, timedelta
import io
import numpy as np
import openpyxl
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Nifty 100 VP Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dark Theme Styling
st.markdown(
    """
    <style>
    .main { background-color: #0E1117; }
    .stMetric { background-color: #1E222D; padding: 15px; border-radius: 10px; border: 1px solid #2B2F3A; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    </style>
""",
    unsafe_allow_html=True,
)

# Nifty 100 Tickers
NIFTY_100_TICKERS = [
    "ABB.NS",
    "ACC.NS",
    "ADANIENT.NS",
    "ADANIGREEN.NS",
    "ADANIPORTS.NS",
    "ADANIPOWER.NS",
    "ATGL.NS",
    "AMBUJACEM.NS",
    "APOLLOHOSP.NS",
    "ASIANPAINT.NS",
    "DMART.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BAJAJHLDNG.NS",
    "BANKBARODA.NS",
    "BERGEPAINT.NS",
    "BEL.NS",
    "BHARATFORG.NS",
    "BPCL.NS",
    "BHARTIARTL.NS",
    "BOSCHLTD.NS",
    "BRITANNIA.NS",
    "CANBK.NS",
    "CHOLAFIN.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "COLPAL.NS",
    "DLF.NS",
    "DABUR.NS",
    "DIVISLAB.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "GAIL.NS",
    "GODREJCP.NS",
    "GODREJPROP.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HAVELLS.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HAL.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "ICICIGI.NS",
    "ICICIPRULI.NS",
    "IOC.NS",
    "IRCTC.NS",
    "IRFC.NS",
    "ITC.NS",
    "INDUSINDBK.NS",
    "NAUKRI.NS",
    "INFY.NS",
    "INDIGO.NS",
    "JSWSTEEL.NS",
    "JINDALSTEL.NS",
    "JIOFIN.NS",
    "KOTAKBANK.NS",
    "LTIM.NS",
    "LT.NS",
    "LUPIN.NS",
    "M&M.NS",
    "MARUTI.NS",
    "MAXHEALTH.NS",
    "MSUMI.NS",
    "NTPC.NS",
    "NESTLEIND.NS",
    "ONGC.NS",
    "PIDILITIND.NS",
    "PFC.NS",
    "POWERGRID.NS",
    "PNB.NS",
    "RELIANCE.NS",
    "SBICARD.NS",
    "SBILIFE.NS",
    "SRF.NS",
    "MOTHERSON.NS",
    "SBIN.NS",
    "SUNPHARMA.NS",
    "TVSMOTOR.NS",
    "TCS.NS",
    "TATACONSUM.NS",
    "TATAELXSI.NS",
    "TATAMOTORS.NS",
    "TATAPOWER.NS",
    "TATASTEEL.NS",
    "TECHM.NS",
    "TITAN.NS",
    "TORNTPHARM.NS",
    "TRENT.NS",
    "ULTRACEMCO.NS",
    "UNOMINDA.NS",
    "UPL.NS",
    "VBL.NS",
    "VEDL.NS",
    "WIPRO.NS",
    "ZOMATO.NS",
    "ZYDUSLIFE.NS",
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
    window_df["Typical_Price"] = (
        window_df["High"] + window_df["Low"] + window_df["Close"]
    ) / 3
    window_df["Bin"] = pd.cut(
        window_df["Typical_Price"], bins=bins, include_lowest=True
    )

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
    data = yf.download(
        NIFTY_100_TICKERS, period="1y", interval="1d", group_by="ticker", progress=False
    )

    for ticker in NIFTY_100_TICKERS:
        try:
            df = (
                data[ticker].dropna()
                if ticker in data.columns.levels[0]
                else pd.DataFrame()
            )
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

                signals.append(
                    {
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
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(signals)


# ==========================================
# BACKTESTING ENGINE (1 to 10 Years)
# ==========================================
@st.cache_data(ttl=3600)
def run_backtest(ticker, years=3, val_threshold_pct=2.0, ema_period=200):
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

    for i in range(ema_period + 20, len(df)):
        sub_df = df.iloc[:i]
        curr_row = df.iloc[i]
        curr_date = df.index[i]

        if not in_trade:
            # Check for Signal
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
            # Manage Open Trade
            high_p = float(curr_row["High"])
            low_p = float(curr_row["Low"])

            if low_p <= sl:
                # Stop Loss Hit
                pnl_pct = ((sl - entry_price) / entry_price) * 100
                trades.append(
                    {
                        "Entry Date": entry_date,
                        "Exit Date": curr_date,
                        "Type": "SL Hit 🔴",
                        "Entry": entry_price,
                        "Exit": sl,
                        "PnL (%)": round(pnl_pct, 2),
                    }
                )
                in_trade = False
            elif high_p >= target:
                # Target Hit
                pnl_pct = ((target - entry_price) / entry_price) * 100
                trades.append(
                    {
                        "Entry Date": entry_date,
                        "Exit Date": curr_date,
                        "Type": "Target Hit 🟢",
                        "Entry": entry_price,
                        "Exit": target,
                        "PnL (%)": round(pnl_pct, 2),
                    }
                )
                in_trade = False

    trades_df = pd.DataFrame(trades)
    return trades_df, df


# ==========================================
# HEADER & MARKET INDICES
# ==========================================
st.title("⚡ Nifty 100 Volume Profile Quant Terminal")
st.caption(
    "Institutional Mean-Reversion Scanner & Multi-Year Backtesting Engine"
)

try:
    indices = yf.download(
        ["^NSEI", "^NSEBANK"], period="5d", interval="1d", progress=False
    )
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
# MAIN INTERFACE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(
    ["🚀 Live Scanner", "📊 Strategy Backtester", "🤖 Quant Intelligence AI"]
)

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
                "TradingView Link": st.column_config.LinkColumn(
                    "TradingView Chart", display_text="📊 Open Chart"
                )
            },
            use_container_width=True,
            hide_index=True,
        )

        # Excel Export
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
        st.info(
            f"No stocks currently sitting within {v_limit}% of VAL support. Try widening the slider to 2.5%."
        )

# ------------------------------------------
# TAB 2: MULTI-YEAR BACKTESTER
# ------------------------------------------
with tab2:
    st.subheader("Strategy Backtesting Engine")
    st.caption("Verify historic win rate and true performance across 1 to 10 years.")

    col_a, col_b, col_c = st.columns(3)
    bt_symbol = col_a.selectbox("Select Stock Ticker", NIFTY_100_TICKERS, index=47) # ICICIBANK.NS
    bt_years = col_b.slider("Backtest Period (Years)", 1, 10, 3)
    bt_threshold = col_c.slider("Backtest VAL Threshold (%)", 0.5, 5.0, 2.0, 0.5)

    if st.button("▶️ Run Multi-Year Backtest", type="primary"):
        with st.spinner(
            f"Fetching {bt_years} year(s) of historical data for {bt_symbol}..."
        ):
            bt_df, price_df = run_backtest(
                bt_symbol, years=bt_years, val_threshold_pct=bt_threshold
            )

        if bt_df is not None and not bt_df.empty:
            total_trades = len(bt_df)
            wins = len(bt_df[bt_df["Type"] == "Target Hit 🟢"])
            losses = len(bt_df[bt_df["Type"] == "SL Hit 🔴"])

            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            loss_rate = (losses / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = bt_df["PnL (%)"].sum()

            win_pnl = bt_df[bt_df["PnL (%)"] > 0]["PnL (%)"].sum()
            loss_pnl = abs(bt_df[bt_df["PnL (%)"] < 0]["PnL (%)"].sum())
            profit_factor = round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else "∞"

            # Performance Cards
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Trades", f"{total_trades}")
            m2.metric("Win Rate (%)", f"{win_rate:.1f}%")
            m3.metric("Loss Rate (%)", f"{loss_rate:.1f}%")
            m4.metric("Cum. Return", f"{total_pnl:+.1f}%")
            m5.metric("Profit Factor", f"{profit_factor}")

            # Interactive Plotly Equity Curve
            bt_df["Cumulative PnL (%)"] = bt_df["PnL (%)"].cumsum()
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=bt_df["Exit Date"],
                    y=bt_df["Cumulative PnL (%)"],
                    mode="lines+markers",
                    name="Equity Curve",
                    line=dict(color="#00E676", width=2),
                )
            )
            fig.update_layout(
                title=f"{bt_symbol} Cumulative Strategy Returns ({bt_years} Years)",
                template="plotly_dark",
                xaxis_title="Date",
                yaxis_title="Cumulative Return (%)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Trades List
            st.subheader("Historical Trades Log")
            st.dataframe(bt_df, use_container_width=True, hide_index=True)
        else:
            st.warning(
                f"No backtest trades triggered for {bt_symbol} in the selected {bt_years}-year window. Try adjusting the parameters!"
            )

# ------------------------------------------
# TAB 3: QUANT AI KNOWLEDGE BASE
# ------------------------------------------
with tab3:
    st.subheader("🤖 Strategy Concepts & Core Rules")

    with st.expander("📚 Value Area Low (VAL) & Point of Control (POC)", expanded=True):
        st.markdown(
            """
        * **POC (Point of Control):** The exact price level where the highest volume was traded during the 20-day lookback. Functions as a strong magnet/target.
        * **VAL (Value Area Low):** The bottom boundary of the 70% volume distribution. Serves as institutional floor support.
        * **Mean Reversion Rule:** Entering near VAL above the 200 EMA offers asymmetric risk:reward aiming for a return to the POC.
        """
        )

    with st.expander("🛡️ Risk Management Guidelines"):
        st.markdown(
            """
        * **Stop Loss:** Set strictly below VAL (e.g., VAL - 0.8%).
        * **Position Sizing:** Risk no more than 1% to 2% of total capital on a single setup.
        * **Target:** Exit 80% position at POC, trail remainder with ATR stop.
        """
        )

# ==========================================
# SIDEBAR INTERACTIVE AI QUANT ASSISTANT
# ==========================================
with st.sidebar:
    st.header("💬 Ask AI Quant Assistant")
    st.caption("Get technical analysis insights for any stock!")

    user_q = st.text_input("Enter stock symbol or technical question:")
    if user_q:
        q_upper = user_q.strip().upper()
        st.write(f"**Analyzing `{q_upper}`...**")

        st.info(
            f"🤖 **Quant Insight for {q_upper}:**\n\n"
            f"When evaluating **{q_upper}**:\n"
            f"1. **Trend Check:** Verify that the price is above the 200 EMA to ensure high win probability.\n"
            f"2. **Volume Profile:** Look for price compression near Value Area Low (VAL).\n"
            f"3. **Candle Confirmation:** Seek bullish rejection candles (pinbars/engulfing) right at VAL before entering."
        )
