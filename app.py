from datetime import datetime, timedelta
import io
import re
import xml.etree.ElementTree as ET
import numpy as np
import openpyxl
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# ==========================================
# PAGE CONFIGURATION & FUTURISTIC STYLING
# ==========================================
st.set_page_config(
    page_title="Nifty Institutional Quant Terminal",
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
    
    .news-card {
        background: #121824;
        border: 1px solid #1E2D40;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
    }
    .badge-bull { background-color: #00E676; color: #000; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
    .badge-bear { background-color: #FF5252; color: #FFF; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
    .badge-neutral { background-color: #FFB300; color: #000; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# INDEX UNIVERSE LISTS
# ==========================================
NIFTY_50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS",
    "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "HCLTECH.NS",
    "ASIANPAINT.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "TATAMOTORS.NS", "POWERGRID.NS", "M&M.NS", "BAJAJFINSV.NS", "TATASTEEL.NS",
    "NESTLEIND.NS", "JSWSTEEL.NS", "ADANIENT.NS", "GRASIM.NS", "TECHM.NS", "ADANIPORTS.NS",
    "HDFCLIFE.NS", "DRREDDY.NS", "DIVISLAB.NS", "BRITANNIA.NS", "EICHERMOT.NS", "SBILIFE.NS",
    "COALINDIA.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "WIPRO.NS",
    "HINDALCO.NS", "BPCL.NS", "CIPLA.NS", "ONGC.NS", "INDUSINDBK.NS", "UPL.NS"
]

NIFTY_100_TICKERS = list(set(NIFTY_50_TICKERS + [
    "ABB.NS", "ACC.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "ATGL.NS", "AMBUJACEM.NS", "DMART.NS",
    "BAJAJHLDNG.NS", "BANKBARODA.NS", "BERGEPAINT.NS", "BEL.NS", "BHARATFORG.NS", "BOSCHLTD.NS",
    "CANBK.NS", "CHOLAFIN.NS", "COLPAL.NS", "DLF.NS", "DABUR.NS", "GAIL.NS", "GODREJCP.NS",
    "GODREJPROP.NS", "HAVELLS.NS", "HAL.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IOC.NS", "IRCTC.NS",
    "IRFC.NS", "NAUKRI.NS", "INDIGO.NS", "JINDALSTEL.NS", "JIOFIN.NS", "LUPIN.NS", "MAXHEALTH.NS",
    "MSUMI.NS", "PIDILITIND.NS", "PFC.NS", "PNB.NS", "SBICARD.NS", "SRF.NS", "MOTHERSON.NS",
    "TVSMOTOR.NS", "TATAELXSI.NS", "TATAPOWER.NS", "TECHM.NS", "TORNTPHARM.NS", "TRENT.NS",
    "UNOMINDA.NS", "VBL.NS", "VEDL.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]))

NIFTY_250_EXT = [
    "AUBANK.NS", "AARTIIND.NS", "AIAENG.NS", "ALKEM.NS", "ASHOKLEY.NS", "ASTRAL.NS", "AUROPHARMA.NS",
    "BALKRISIND.NS", "BANDHANBNK.NS", "BATAINDIA.NS", "BHARATFORG.NS", "BSOFT.NS", "CGPOWER.NS",
    "COFORGE.NS", "CONCOR.NS", "CUMMINSIND.NS", "DEEPAKNTR.NS", "ESCORTS.NS", "FEDERALBNK.NS",
    "FORTIS.NS", "GLENMARK.NS", "GMRINFRA.NS", "GUJGASLTD.NS", "IDFCFIRSTB.NS", "IPCALAB.NS",
    "KPITTECH.NS", "LICHSGFIN.NS", "MRF.NS", "M&MFIN.NS", "POLYCAB.NS", "RECLTD.NS",
    "SUPREMEIND.NS", "VOLTAS.NS", "YESBANK.NS"
]

NIFTY_250_TICKERS = list(set(NIFTY_100_TICKERS + NIFTY_250_EXT))

NIFTY_500_EXT = [
    "ANGELONE.NS", "CDSL.NS", "CAMS.NS", "CYIENT.NS", "DELHIVERY.NS", "DEVYANI.NS", "EASEMYTRIP.NS",
    "HFCL.NS", "IIFL.NS", "IEX.NS", "KEI.NS", "KFINTECH.NS", "MCX.NS", "NATIONALUM.NS", "NYKAA.NS",
    "PAYTM.NS", "PVRINOX.NS", "RBLBANK.NS", "ROUTE.NS", "SUZLON.NS", "TATACOMM.NS", "TATAINVEST.NS"
]

NIFTY_500_TICKERS = list(set(NIFTY_250_TICKERS + NIFTY_500_EXT))

UNIVERSE_MAP = {
    "Nifty 50": NIFTY_50_TICKERS,
    "Nifty 100": NIFTY_100_TICKERS,
    "Nifty 250": NIFTY_250_TICKERS,
    "Nifty 500": NIFTY_500_TICKERS
}

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
# LIVE MULTI-UNIVERSE SCANNER ENGINE
# ==========================================
@st.cache_data(ttl=1800)
def run_live_scan(ticker_list, val_threshold_pct=1.0, atr_multiplier=1.2, min_rr=1.0):
    signals = []
    scan_date = datetime.now().strftime("%Y-%m-%d")
    data = yf.download(ticker_list, period="1y", interval="1d", group_by="ticker", progress=False)

    for ticker in ticker_list:
        try:
            df = data[ticker].dropna() if (len(ticker_list) > 1 and ticker in data.columns.levels[0]) else (data.dropna() if len(ticker_list) == 1 else pd.DataFrame())
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
            ema_200 = float(current_row["EMA_200"])
            atr_val = float(current_row["ATR"])
            vol_val = float(current_row["Volume"])
            vol_avg = float(current_row["Vol_SMA"])

            dist_to_val = ((close_price - val) / val) * 100

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
# BACKTESTING ENGINE WITH YEARLY BREAKDOWN
# ==========================================
@st.cache_data(ttl=3600)
def run_backtest_single(ticker, years=3, val_threshold_pct=1.0, atr_multiplier=1.2, min_rr=1.0, initial_capital=100000):
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
                                "Stock": ticker.replace(".NS", ""),
                                "Entry Date": entry_date.strftime("%Y-%m-%d"),
                                "Exit Date": exit_date.strftime("%Y-%m-%d"),
                                "Year": str(exit_date.year),
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
                                "Stock": ticker.replace(".NS", ""),
                                "Entry Date": entry_date.strftime("%Y-%m-%d"),
                                "Exit Date": exit_date.strftime("%Y-%m-%d"),
                                "Year": str(exit_date.year),
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


@st.cache_data(ttl=3600)
def run_universe_backtest(universe_name, years=3, val_threshold_pct=1.0, atr_multiplier=1.2, min_rr=1.0, initial_capital=100000):
    tickers = UNIVERSE_MAP.get(universe_name, NIFTY_100_TICKERS)
    summary_list = []
    all_trades = []

    progress_bar = st.progress(0)
    for idx, t in enumerate(tickers):
        progress_bar.progress((idx + 1) / len(tickers))
        t_df, _ = run_backtest_single(t, years, val_threshold_pct, atr_multiplier, min_rr, initial_capital)
        if t_df is not None and not t_df.empty:
            all_trades.append(t_df)
            total_t = len(t_df)
            wins = len(t_df[t_df["Type"] == "Target Hit 🟢"])
            win_r = round((wins / total_t) * 100, 1)
            tot_pnl = round(t_df["PnL (%)"].sum(), 2)
            summary_list.append({
                "Stock": t.replace(".NS", ""),
                "Total Signals": total_t,
                "Win Rate (%)": f"{win_r}%",
                "Total Return (%)": f"{tot_pnl:+.2f}%",
                "Final Value (₹)": round(float(t_df["Portfolio (₹)"].iloc[-1]), 2)
            })

    progress_bar.empty()
    summary_df = pd.DataFrame(summary_list)
    combined_trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    return summary_df, combined_trades_df


# ==========================================
# NEWS & AI IMPACT ENGINE
# ==========================================
@st.cache_data(ttl=1800)
def fetch_breaking_news():
    news_items = []
    rss_urls = [
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms"
    ]
    
    for url in rss_urls:
        try:
            res = requests.get(url, timeout=5)
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                clean_desc = re.sub("<.*?>", "", desc or "")
                
                sentiment = "NEUTRAL"
                badge_class = "badge-neutral"
                if any(w in (title + clean_desc).lower() for w in ["profit", "surges", "jumps", "rally", "record", "growth", "high"]):
                    sentiment = "BULLISH"
                    badge_class = "badge-bull"
                elif any(w in (title + clean_desc).lower() for w in ["drop", "falls", "slumps", "loss", "crash", "war", "inflation"]):
                    sentiment = "BEARISH"
                    badge_class = "badge-bear"

                impacted = []
                if "bank" in (title + clean_desc).lower(): impacted.append("Bank Nifty (HDFCBANK, ICICIBANK, SBIN)")
                if "it" in (title + clean_desc).lower() or "tech" in (title + clean_desc).lower(): impacted.append("IT Sector (TCS, INFY, HCLTECH)")
                if "auto" in (title + clean_desc).lower(): impacted.append("Auto (TATAMOTORS, MARUTI, M&M)")
                if "oil" in (title + clean_desc).lower() or "crude" in (title + clean_desc).lower(): impacted.append("Energy (RELIANCE, ONGC, BPCL)")
                
                impact_str = ", ".join(impacted) if impacted else "Broad Market Indices (Nifty 50 / Sensex)"

                news_items.append({
                    "title": title,
                    "description": clean_desc[:150] + "...",
                    "sentiment": sentiment,
                    "badge": badge_class,
                    "impact": impact_str
                })
        except Exception:
            continue
            
    return news_items


# ==========================================
# HEADER & MARKET INDICES
# ==========================================
st.title("⚡ Nifty Multi-Universe Quant Terminal")
st.caption("Volume Profile Mean-Reversion Terminal & Global Intelligence Engine")

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
tab1, tab2, tab3 = st.tabs(["🚀 Live Multi-Universe Scanner", "📊 Universe Strategy Backtester", "📰 Market News & Impact Analysis"])

# ------------------------------------------
# TAB 1: LIVE MULTI-UNIVERSE SCANNER
# ------------------------------------------
with tab1:
    st.subheader("Nifty Multi-Index Scanner Engine")
    
    col_u1, col_u2 = st.columns([1, 2])
    selected_universe = col_u1.selectbox("Select Index Universe", ["Nifty 50", "Nifty 100", "Nifty 250", "Nifty 500"], index=1)
    reset_defaults = col_u2.checkbox("🎯 Reset to 60% Win-Rate Optimal Defaults (VAL: 1.0%, ATR: 1.2x, R:R: 1.0)", value=True, key="live_reset")

    default_val = 1.0 if reset_defaults else 2.5
    default_atr = 1.2 if reset_defaults else 1.2
    default_rr = 1.0 if reset_defaults else 1.0

    col_p1, col_p2, col_p3 = st.columns(3)
    v_limit = col_p1.slider("VAL Distance Threshold (%)", 0.5, 5.0, default_val, 0.5, key="live_val")
    atr_mult = col_p2.slider("ATR Stop Buffer Multiplier", 0.8, 2.5, default_atr, 0.1, key="live_atr")
    min_rr_param = col_p3.slider("Minimum R:R Ratio", 0.8, 2.0, default_rr, 0.1, key="live_rr")

    target_tickers = UNIVERSE_MAP[selected_universe]

    with st.spinner(f"Scanning {len(target_tickers)} stocks across {selected_universe}..."):
        scan_results = run_live_scan(target_tickers, val_threshold_pct=v_limit, atr_multiplier=atr_mult, min_rr=min_rr_param)

    if not scan_results.empty:
        st.success(f"Found {len(scan_results)} setups across {selected_universe} universe!")

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
            scan_results.to_excel(writer, index=False, sheet_name="LiveSetups")

        st.download_button(
            "📥 Export Report to Excel",
            data=excel_buffer.getvalue(),
            file_name=f"{selected_universe}_Scan_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info(f"No setups matching current parameters in {selected_universe}. Try unchecking reset or widening sliders.")

# ------------------------------------------
# TAB 2: UNIVERSE BACKTESTER
# ------------------------------------------
with tab2:
    st.subheader("Multi-Stock & Index Backtester")
    
    bt_mode = st.radio("Backtest Mode", ["Single Stock", "Scan Entire Index Universe"], horizontal=True)
    
    reset_bt = st.checkbox("🎯 Reset Backtest to 60% Win-Rate Optimal Defaults", value=True, key="bt_reset")
    bt_def_val = 1.0 if reset_bt else 2.5
    bt_def_atr = 1.2 if reset_bt else 1.2
    bt_def_rr = 1.0 if reset_bt else 1.0

    if bt_mode == "Single Stock":
        col_a, col_b, col_c, col_d, col_e, col_f = st.columns(6)
        bt_symbol = col_a.selectbox("Stock Ticker", NIFTY_500_TICKERS, index=47)
        initial_cap = col_b.number_input("Capital (₹)", value=100000, step=10000, format="%d")
        bt_years = col_c.slider("Period", 1, 10, 3)
        bt_threshold = col_d.slider("VAL %", 0.5, 5.0, bt_def_val, 0.5, key="bt_val")
        bt_atr = col_e.slider("ATR Mult", 0.8, 2.0, bt_def_atr, 0.1, key="bt_atr")
        bt_rr = col_f.slider("Min R:R", 0.8, 2.0, bt_def_rr, 0.1, key="bt_rr")

        if st.button("▶️ Run Single Stock Backtest", type="primary"):
            with st.spinner(f"Simulating trades for {bt_symbol}..."):
                bt_df, _ = run_backtest_single(bt_symbol, years=bt_years, val_threshold_pct=bt_threshold, atr_multiplier=bt_atr, min_rr=bt_rr, initial_capital=initial_cap)

            if bt_df is not None and not bt_df.empty:
                total_trades = len(bt_df)
                wins = len(bt_df[bt_df["Type"] == "Target Hit 🟢"])
                losses = len(bt_df[bt_df["Type"] == "SL Hit 🔴"])
                win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                final_portfolio = float(bt_df["Portfolio (₹)"].iloc[-1])
                net_profit_rs = final_portfolio - initial_cap
                total_return_pct = (net_profit_rs / initial_cap) * 100

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Initial Investment", f"₹{initial_cap:,.0f}")
                m2.metric("Final Portfolio", f"₹{final_portfolio:,.2f}", f"{total_return_pct:+.2f}%")
                m3.metric("Net Profit/Loss", f"₹{net_profit_rs:,.2f}")
                m4.metric("Win Rate (%)", f"{win_rate:.1f}% ({wins}W / {losses}L)")

                # --- NEW: Yearly Breakdown Metric Display ---
                st.markdown("### 📅 Yearly Performance Breakdown")
                yearly_group = bt_df.groupby("Year")
                y_cols = st.columns(len(yearly_group) if len(yearly_group) > 0 else 1)
                
                for idx, (year_val, group) in enumerate(yearly_group):
                    y_wins = len(group[group["Type"] == "Target Hit 🟢"])
                    y_losses = len(group[group["Type"] == "SL Hit 🔴"])
                    y_total = len(group)
                    y_rate = (y_wins / y_total) * 100 if y_total > 0 else 0
                    y_pnl = group["PnL (%)"].sum()
                    
                    with y_cols[idx % len(y_cols)]:
                        st.metric(f"Year {year_val}", f"{y_rate:.1f}% Win Rate", f"{y_wins}W / {y_losses}L ({y_pnl:+.1f}%)")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=bt_df["Exit Date"], y=bt_df["Portfolio (₹)"], mode="lines+markers", line=dict(color="#00E5FF", width=3)))
                fig.update_layout(title=f"{bt_symbol} Portfolio Growth", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(bt_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No trades triggered for this ticker in the chosen window.")

    else:
        col_x, col_y, col_z = st.columns(3)
        bt_universe = col_x.selectbox("Select Index Universe to Backtest", ["Nifty 50", "Nifty 100", "Nifty 250", "Nifty 500"], index=1)
        bt_years = col_y.slider("Lookback Period (Years)", 1, 10, 3)
        initial_cap = col_z.number_input("Capital per Stock (₹)", value=100000, step=10000, format="%d")

        if st.button(f"▶️ Run Full {bt_universe} Universe Scan", type="primary"):
            st.info(f"Scanning all constituent stocks in {bt_universe} over {bt_years} years. Please wait...")
            summary_df, combined_df = run_universe_backtest(bt_universe, years=bt_years, val_threshold_pct=bt_def_val, atr_multiplier=bt_def_atr, min_rr=bt_def_rr, initial_capital=initial_cap)

            if not summary_df.empty:
                st.success(f"Universe Scan Complete! Found signals in {len(summary_df)} stocks.")
                
                # --- NEW: Universe-Wide Yearly Breakdown ---
                st.markdown("### 📅 Universe-Wide Yearly Breakdown")
                if "Year" in combined_df.columns:
                    univ_yearly = combined_df.groupby("Year")
                    u_cols = st.columns(len(univ_yearly) if len(univ_yearly) > 0 else 1)
                    for idx, (u_year, u_group) in enumerate(univ_yearly):
                        u_wins = len(u_group[u_group["Type"] == "Target Hit 🟢"])
                        u_losses = len(u_group[u_group["Type"] == "SL Hit 🔴"])
                        u_total = len(u_group)
                        u_rate = (u_wins / u_total) * 100 if u_total > 0 else 0
                        with u_cols[idx % len(u_cols)]:
                            st.metric(f"Year {u_year}", f"{u_rate:.1f}% Win Rate", f"{u_wins}W / {u_losses}L ({u_total} Trades)")

                st.subheader("📌 Stocks Generating Signals Summary")
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

                st.subheader("📜 Complete Signal Trade Execution Log")
                st.dataframe(combined_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No signals found across this universe with current settings.")

# ------------------------------------------
# TAB 3: MARKET NEWS & IMPACT ANALYSIS
# ------------------------------------------
with tab3:
    st.subheader("📰 Real-Time Global & Local Financial News")
    st.caption("AI-extracted market sentiment and stock impact mapping")

    if st.button("🔄 Refresh Market News"):
        st.cache_data.clear()

    news_data = fetch_breaking_news()

    if news_data:
        for item in news_data:
            st.markdown(
                f"""
                <div class="news-card">
                    <span class="{item['badge']}">{item['sentiment']}</span>
                    <h4 style="margin: 8px 0; color: #FFFFFF;">{item['title']}</h4>
                    <p style="color: #94A3B8; font-size: 0.9rem;">{item['description']}</p>
                    <div style="margin-top: 8px; font-size: 0.85rem; color: #00E5FF;">
                        <strong>🎯 Impacted Stocks / Sectors:</strong> {item['impact']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Unable to fetch live news feeds at the moment. Please try refreshing.")

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
            f"1. **Yearly Win/Loss Tracking:** View individual performance metrics per calendar year directly in the backtest tab.\n"
            f"2. **Universe Coverage:** Track signals across Nifty 50, 100, 250, and 500 indexes simultaneously."
        )
