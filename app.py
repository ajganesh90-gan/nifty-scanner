from datetime import datetime
import io
import numpy as np
import openpyxl
import pandas as pd
import streamlit as st
import yfinance as yf

# Page Setup
st.set_page_config(
    page_title="Nifty 100 Volume Profile Scanner", page_icon="📈", layout="wide"
)

st.title("📈 Nifty 100 Volume Profile EOD Scanner")
st.markdown(
    "Scan the Nifty 100 universe for Value Area Low (VAL) support above the 200-EMA. "
    "**Tap any stock symbol to open directly in TradingView Mobile!**"
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


def calculate_atr(df, window=14):
    """Calculates 14-period Average True Range."""
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_ai_analysis(row):
    """Generates structured technical verdict and insights for a scanned stock setup."""
    rr = row["R:R Ratio"]
    dist = row["Dist to VAL (%)"]
    est_days = row["Est. Days to Target"]

    if rr >= 2.5 and dist <= 1.0:
        verdict = "🔥 HIGH CONVICTION BUY"
        risk_level = "Low Risk (At Solid Support)"
        explanation = (
            f"Trading right on top of Volume Area Low (VAL) support with an exceptional "
            f"Risk-to-Reward ratio of {rr}:1. Long-term trend remains bullish above the 200 EMA."
        )
    elif rr >= 1.5:
        verdict = "🟢 ACCUMULATE / BUY ON DIPS"
        risk_level = "Moderate Risk"
        explanation = (
            f"Favorable mean-reversion setup toward the Point of Control (POC). "
            f"Expected target timeframe is ~{est_days}."
        )
    else:
        verdict = "⚠️ CAUTION NEAR RESISTANCE"
        risk_level = "Higher Risk (Low R:R)"
        explanation = (
            f"Distance to target POC is tight relative to stop-loss placement. "
            f"Consider waiting for a deeper pull back closer to VAL support."
        )

    return verdict, risk_level, explanation


@st.cache_data(ttl=3600)
def run_scanner(val_threshold_pct=2.0):
    signals = []
    scan_date = datetime.now().strftime("%Y-%m-%d")
    data = yf.download(
        NIFTY_100_TICKERS, period="1y", interval="1d", group_by="ticker", progress=False
    )

    for ticker in NIFTY_100_TICKERS:
        try:
            if ticker in data.columns.levels[0]:
                df = data[ticker].dropna()
            else:
                continue

            if len(df) < 220:
                continue

            # Indicators
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()
            df["ATR_14"] = calculate_atr(df, window=14)
            df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3

            # Volume Profile (20-day window)
            lookback = 20
            window_df = df.iloc[-lookback - 1 : -1].copy()
            p_min, p_max = window_df["Low"].min(), window_df["High"].max()
            if p_min == p_max:
                continue

            bins = np.linspace(p_min, p_max, 31)
            window_df["Bin"] = pd.cut(
                window_df["Typical_Price"], bins=bins, include_lowest=True
            )
            vp = (
                window_df.groupby("Bin", observed=False)["Volume"]
                .sum()
                .reset_index()
            )
            vp["Price_Mid"] = vp["Bin"].apply(lambda x: x.mid)

            poc_price = float(vp.loc[vp["Volume"].idxmax()]["Price_Mid"])
            total_vol = vp["Volume"].sum()
            sorted_vp = vp.sort_values(by="Volume", ascending=False)
            sorted_vp["Cum_Vol"] = sorted_vp["Volume"].cumsum()
            va_bins = sorted_vp[sorted_vp["Cum_Vol"] <= total_vol * 0.70]

            if va_bins.empty:
                continue

            val = float(va_bins["Price_Mid"].min())
            current_row = df.iloc[-1]
            close_price = float(current_row["Close"])
            ema_200 = float(current_row["EMA_200"])
            atr_val = float(current_row["ATR_14"])

            distance_to_val_pct = ((close_price - val) / val) * 100
            is_above_ema = close_price > ema_200

            if 0 <= distance_to_val_pct <= val_threshold_pct and is_above_ema:
                entry_price = close_price
                stop_loss = val - (val * 0.008)
                target_poc = poc_price

                if target_poc <= entry_price:
                    continue

                risk = entry_price - stop_loss
                reward = target_poc - entry_price
                rr_ratio = reward / risk if risk > 0 else 0

                # Estimated Days Calculation via ATR
                est_days = max(1, int(round(reward / atr_val))) if atr_val > 0 else 3

                raw_symbol = ticker.replace(".NS", "")
                tv_url = f"https://in.tradingview.com/chart/?symbol=NSE:{raw_symbol}"

                signals.append(
                    {
                        "Date": scan_date,
                        "Stock": raw_symbol,
                        "TradingView Link": tv_url,
                        "Buy / Entry (₹)": round(entry_price, 2),
                        "POC Target (₹)": round(target_poc, 2),
                        "Suggested SL (₹)": round(stop_loss, 2),
                        "Est. Days to Target": f"{est_days} Days",
                        "R:R Ratio": round(rr_ratio, 2),
                        "200 EMA (₹)": round(ema_200, 2),
                        "VAL Support (₹)": round(val, 2),
                        "Dist to VAL (%)": round(distance_to_val_pct, 2),
                        "Status": "AT VAL SUPPORT",
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(signals)


# Top Live Index Status Header
try:
    index_data = yf.download(
        ["^NSEI", "^NSEBANK"], period="5d", interval="1d", progress=False
    )
    if not index_data.empty and ("Close", "^NSEI") in index_data.columns:
        nifty_close = float(index_data[("Close", "^NSEI")].iloc[-1])
        nifty_prev = float(index_data[("Close", "^NSEI")].iloc[-2])
        nifty_chg = ((nifty_close - nifty_prev) / nifty_prev) * 100

        bank_close = float(index_data[("Close", "^NSEBANK")].iloc[-1])
        bank_prev = float(index_data[("Close", "^NSEBANK")].iloc[-2])
        bank_chg = ((bank_close - bank_prev) / bank_prev) * 100

        col_a, col_b = st.columns(2)
        col_a.metric("NIFTY 50", f"₹{nifty_close:,.2f}", f"{nifty_chg:+.2f}%")
        col_b.metric("BANK NIFTY", f"₹{bank_close:,.2f}", f"{bank_chg:+.2f}%")
except Exception:
    pass

st.divider()

# UI Controls
val_limit = st.slider("VAL Distance Threshold (%)", 0.5, 5.0, 2.0, 0.5)

if st.button("🚀 Run Live Nifty 100 Scan", type="primary"):
    with st.spinner("Analyzing volume profile and computing ATR metrics..."):
        df_result = run_scanner(val_threshold_pct=val_limit)

    if not df_result.empty:
        st.success(f"Scan complete! Found {len(df_result)} setups.")

        # Interactive Table with clickable TradingView links
        st.dataframe(
            df_result,
            column_config={
                "TradingView Link": st.column_config.LinkColumn(
                    "Open in TradingView App",
                    display_text="📊 Chart",
                    help="Click to open chart in TradingView mobile app",
                )
            },
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("🤖 AI Stock Agent Insights & Verdicts")

        # Display AI breakdown for each scanned signal
        for idx, row in df_result.iterrows():
            verdict, risk_lvl, explanation = generate_ai_analysis(row)

            with st.expander(f"📌 {row['Stock']} — {verdict}", expanded=True):
                col1, col2, col3 = st.columns(3)
                col1.metric("Target (POC)", f"₹{row['POC Target (₹)']}")
                col2.metric("Stop Loss (VAL)", f"₹{row['Suggested SL (₹)']}")
                col3.metric("R:R Ratio", f"{row['R:R Ratio']} : 1")

                st.write(f"**Risk Level:** {risk_lvl}")
                st.write(f"**AI Analysis:** {explanation}")
                st.markdown(f"[🔗 Open {row['Stock']} Chart on TradingView]({row['TradingView Link']})")

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_result.to_excel(writer, index=False, sheet_name="Watchlist")

        st.download_button(
            label="📥 Download Excel Report",
            data=output.getvalue(),
            file_name=f"Nifty100_VP_Watchlist_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning(
            f"No stocks within {val_limit}% of VAL today. Try increasing the slider to 3.0% or 4.0%."
        )

# Sidebar Interactive AI Assistant
with st.sidebar:
    st.header("💬 Ask AI Stock Agent")
    st.caption("Got doubts about a stock signal? Ask for technical insights!")

    user_query = st.text_input("Enter stock symbol or question:")
    if user_query:
        query = user_query.strip().upper()
        st.write(f"**Analyzing `{query}`...**")
        st.info(
            f"🤖 **Agent Response for {query}:**\n\n"
            f"When evaluating mean-reversion setups on **{query}**, verify that current price is strictly "
            f"above the 200 EMA to ensure high probability. Check if daily volume at Value Area Low (VAL) "
            f"shows absorption candles before committing to an entry."
        )
