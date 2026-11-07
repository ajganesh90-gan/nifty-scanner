from __future__ import annotations

from datetime import datetime, timedelta
import io
import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# ============================================================
# PAGE + THEME
# ============================================================
st.set_page_config(
    page_title="Nifty Institutional Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color:#07090E; color:#E2E8F0; font-family:Inter,sans-serif; }
    h1,h2,h3 { color:#00E5FF !important; font-weight:700; letter-spacing:-.5px; }
    div[data-testid="stMetric"] { background:linear-gradient(135deg,#121824 0%,#1A2332 100%); border:1px solid #1E2D40; padding:16px; border-radius:12px; }
    div[data-testid="stMetric"] label { color:#94A3B8 !important; font-weight:600; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color:#FFF !important; font-size:1.5rem; font-weight:700; }
    .stTabs [data-baseweb="tab-list"] { gap:8px; background:#0B0E14; padding:6px; border-radius:12px; border:1px solid #1E2D40; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background:linear-gradient(135deg,#00E5FF 0%,#00838F 100%) !important; color:#07090E !important; }
    .news-card { background:#121824; border:1px solid #1E2D40; border-radius:10px; padding:15px; margin-bottom:12px; }
    .badge-bull { background:#00E676; color:#000; padding:3px 8px; border-radius:4px; font-weight:700; font-size:.75rem; }
    .badge-bear { background:#FF5252; color:#FFF; padding:3px 8px; border-radius:4px; font-weight:700; font-size:.75rem; }
    .badge-neutral { background:#FFB300; color:#000; padding:3px 8px; border-radius:4px; font-weight:700; font-size:.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# FALLBACK UNIVERSES. Live official CSVs are preferred below.
# These lists are only fallbacks and are not guaranteed current.
# ============================================================
NIFTY_50_FALLBACK = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS",
    "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "HCLTECH.NS",
    "ASIANPAINT.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "TATAMOTORS.NS", "POWERGRID.NS", "M&M.NS", "BAJAJFINSV.NS", "TATASTEEL.NS",
    "NESTLEIND.NS", "JSWSTEEL.NS", "ADANIENT.NS", "GRASIM.NS", "TECHM.NS", "ADANIPORTS.NS",
    "HDFCLIFE.NS", "DRREDDY.NS", "DIVISLAB.NS", "BRITANNIA.NS", "EICHERMOT.NS", "SBILIFE.NS",
    "COALINDIA.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "WIPRO.NS",
    "HINDALCO.NS", "BPCL.NS", "CIPLA.NS", "ONGC.NS", "INDUSINDBK.NS", "UPL.NS",
]

INDEX_CSV_URLS = {
    "Nifty 50": "https://www.niftyindices.com/Index_Constituent/ind_nifty50list.csv",
    "Nifty 100": "https://www.niftyindices.com/Index_Constituent/ind_nifty100list.csv",
    "Nifty 250": "https://www.niftyindices.com/Index_Constituent/ind_nifty250list.csv",
    "Nifty 500": "https://www.niftyindices.com/Index_Constituent/ind_nifty500list.csv",
}


def _normalise_symbol(value: str) -> Optional[str]:
    symbol = str(value).strip().upper()
    if not symbol or symbol in {"NAN", "NONE"}:
        return None
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def load_universe_lists() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    nifty_100_fallback = list(dict.fromkeys(NIFTY_50_FALLBACK + [
        "ABB.NS", "ACC.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "ATGL.NS", "AMBUJACEM.NS", "DMART.NS",
        "BAJAJHLDNG.NS", "BANKBARODA.NS", "BERGEPAINT.NS", "BEL.NS", "BHARATFORG.NS", "BOSCHLTD.NS",
        "CANBK.NS", "CHOLAFIN.NS", "COLPAL.NS", "DLF.NS", "DABUR.NS", "GAIL.NS", "GODREJCP.NS",
        "GODREJPROP.NS", "HAVELLS.NS", "HAL.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IOC.NS", "IRCTC.NS",
        "IRFC.NS", "NAUKRI.NS", "INDIGO.NS", "JINDALSTEL.NS", "JIOFIN.NS", "LUPIN.NS", "MAXHEALTH.NS",
        "MSUMI.NS", "PIDILITIND.NS", "PFC.NS", "PNB.NS", "SBICARD.NS", "SRF.NS", "MOTHERSON.NS",
        "TVSMOTOR.NS", "TATAELXSI.NS", "TATAPOWER.NS", "TORNTPHARM.NS", "TRENT.NS", "UNOMINDA.NS",
        "VBL.NS", "VEDL.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
    ]))
    nifty_250_fallback = list(dict.fromkeys(nifty_100_fallback + [
        "AUBANK.NS", "AARTIIND.NS", "AIAENG.NS", "ALKEM.NS", "ASHOKLEY.NS", "ASTRAL.NS", "AUROPHARMA.NS",
        "BALKRISIND.NS", "BANDHANBNK.NS", "BATAINDIA.NS", "BSOFT.NS", "CGPOWER.NS", "COFORGE.NS", "CONCOR.NS",
        "CUMMINSIND.NS", "DEEPAKNTR.NS", "ESCORTS.NS", "FEDERALBNK.NS", "FORTIS.NS", "GLENMARK.NS",
        "GMRINFRA.NS", "GUJGASLTD.NS", "IDFCFIRSTB.NS", "IPCALAB.NS", "KPITTECH.NS", "LICHSGFIN.NS",
        "MRF.NS", "M&MFIN.NS", "POLYCAB.NS", "RECLTD.NS", "SUPREMEIND.NS", "VOLTAS.NS", "YESBANK.NS"
    ]))
    nifty_500_fallback = list(dict.fromkeys(nifty_250_fallback + [
        "ANGELONE.NS", "CDSL.NS", "CAMS.NS", "CYIENT.NS", "DELHIVERY.NS", "DEVYANI.NS", "EASEMYTRIP.NS",
        "HFCL.NS", "IIFL.NS", "IEX.NS", "KEI.NS", "KFINTECH.NS", "MCX.NS", "NATIONALUM.NS", "NYKAA.NS",
        "PAYTM.NS", "PVRINOX.NS", "RBLBANK.NS", "ROUTE.NS", "SUZLON.NS", "TATACOMM.NS", "TATAINVEST.NS"
    ]))
    fallback = {
        "Nifty 50": NIFTY_50_FALLBACK,
        "Nifty 100": nifty_100_fallback,
        "Nifty 250": nifty_250_fallback,
        "Nifty 500": nifty_500_fallback,
    }
    universes: Dict[str, List[str]] = {}
    status: Dict[str, str] = {}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"}
    for name, url in INDEX_CSV_URLS.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            frame = pd.read_csv(io.BytesIO(response.content))
            symbol_col = next((c for c in frame.columns if str(c).strip().lower() == "symbol"), None)
            if symbol_col is None:
                raise ValueError("CSV does not contain a Symbol column")
            symbols = sorted({s for s in (_normalise_symbol(x) for x in frame[symbol_col].dropna()) if s})
            if not symbols:
                raise ValueError("No symbols returned")
            universes[name] = symbols
            status[name] = f"Official constituent CSV loaded ({len(symbols)} symbols)."
        except Exception as exc:
            universes[name] = fallback[name]
            status[name] = f"Official list unavailable; using fallback ({len(fallback[name])} symbols). {type(exc).__name__}"
    return universes, status


UNIVERSE_MAP, UNIVERSE_STATUS = load_universe_lists()

# ============================================================
# DATA + INDICATOR HELPERS
# ============================================================
def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window, min_periods=window).mean()


def calculate_volume_profile(df: pd.DataFrame, lookback: int = 20):
    """Profile only the lookback bars immediately before the current bar."""
    if df is None or len(df) < lookback + 1:
        return None, None, None
    window = df.iloc[-lookback - 1:-1].copy()
    window = window.dropna(subset=["High", "Low", "Close", "Volume"])
    if window.empty:
        return None, None, None
    p_min = float(window["Low"].min())
    p_max = float(window["High"].max())
    if not np.isfinite(p_min + p_max) or p_max <= p_min:
        return None, None, None
    bins = np.linspace(p_min, p_max, 31)
    typical = (window["High"] + window["Low"] + window["Close"]) / 3
    window["Bin"] = pd.cut(typical, bins=bins, include_lowest=True, duplicates="drop")
    vp = window.groupby("Bin", observed=False)["Volume"].sum().reset_index()
    vp = vp[vp["Volume"] > 0].copy()
    if vp.empty:
        return None, None, None
    vp["Price_Mid"] = vp["Bin"].map(lambda interval: interval.mid)
    vp = vp.sort_values("Volume", ascending=False).reset_index(drop=True)
    total_volume = float(vp["Volume"].sum())
    if total_volume <= 0:
        return None, None, None
    poc = float(vp.iloc[0]["Price_Mid"])
    vp["Cum_Vol"] = vp["Volume"].cumsum()
    # Include the bin that crosses the 70% threshold.
    value_area = vp[(vp["Cum_Vol"] - vp["Volume"]) < total_volume * 0.70]
    if value_area.empty:
        value_area = vp.iloc[[0]]
    val = float(value_area["Price_Mid"].min())
    vah = float(value_area["Price_Mid"].max())
    return poc, val, vah


def extract_ticker_frame(data: pd.DataFrame, ticker: str, ticker_count: int) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    frame = data
    if isinstance(frame.columns, pd.MultiIndex):
        level0 = frame.columns.get_level_values(0)
        level1 = frame.columns.get_level_values(1)
        if ticker in level0:
            frame = frame[ticker]
        elif ticker in level1:
            frame = frame.xs(ticker, axis=1, level=1)
        elif ticker_count == 1:
            frame.columns = frame.columns.get_level_values(0)
        else:
            return pd.DataFrame()
    frame = frame.copy()
    frame.columns = [str(c).title() for c in frame.columns]
    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in frame.columns for c in needed):
        return pd.DataFrame()
    return frame[needed].dropna(subset=["Open", "High", "Low", "Close"]).sort_index()


@st.cache_data(ttl=60 * 60, show_spinner=False)
def download_price_batch(tickers: Tuple[str, ...], start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    return yf.download(
        list(tickers), start=start_date, end=end_date, interval="1d", auto_adjust=False,
        group_by="ticker", progress=False, threads=True, timeout=25,
    )


def iter_chunks(items: List[str], size: int = 35) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


# ============================================================
# V3.0 MARKET REGIME + MULTI-ENGINE SIGNALS
# ============================================================
def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def calculate_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    up = df["High"].diff()
    down = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / window, adjust=False, min_periods=window).mean().fillna(0)


def add_v3_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy().sort_index()
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["EMA50_Slope"] = df["EMA_50"].pct_change(10) * 100
    df["ATR"] = calculate_atr(df, 14)
    df["ATR_PCT"] = df["ATR"] / df["Close"].replace(0, np.nan) * 100
    df["Vol_SMA"] = df["Volume"].rolling(20, min_periods=15).mean()
    df["RSI"] = calculate_rsi(df["Close"], 14)
    df["ADX"] = calculate_adx(df, 14)
    mid = df["Close"].rolling(20, min_periods=20).mean()
    std = df["Close"].rolling(20, min_periods=20).std(ddof=0)
    df["BB_UPPER"] = mid + 2 * std
    df["BB_LOWER"] = mid - 2 * std
    df["BB_WIDTH"] = (df["BB_UPPER"] - df["BB_LOWER"]) / mid.replace(0, np.nan)
    df["BB_WIDTH_PCTL"] = df["BB_WIDTH"].rolling(126, min_periods=40).rank(pct=True)
    df["ROC_20"] = df["Close"].pct_change(20) * 100
    df["PRIOR_20_HIGH"] = df["High"].rolling(20).max().shift(1)
    df["PRIOR_20_LOW"] = df["Low"].rolling(20).min().shift(1)
    return df


def build_market_regime_series(index_frame: pd.DataFrame) -> pd.Series:
    """Classify the broad market from Nifty index daily bars; uses only information available on each date."""
    if index_frame is None or index_frame.empty or len(index_frame) < 210:
        return pd.Series(dtype="object")
    idx = add_v3_indicators(index_frame)
    regimes = []
    for _, row in idx.iterrows():
        if pd.isna(row.get("EMA_200")) or pd.isna(row.get("ADX")):
            regimes.append("UNKNOWN")
        elif row["Close"] > row["EMA_50"] > row["EMA_200"] and row["EMA50_Slope"] > 0.10 and row["ADX"] >= 18:
            regimes.append("BULL")
        elif row["Close"] < row["EMA_50"] < row["EMA_200"] and row["EMA50_Slope"] < -0.10 and row["ADX"] >= 18:
            regimes.append("BEAR")
        else:
            regimes.append("SIDEWAYS")
    return pd.Series(regimes, index=idx.index, name="Market Regime")


def regime_for_date(regime_series: Optional[pd.Series], date, fallback: str = "SIDEWAYS") -> str:
    if regime_series is None or regime_series.empty:
        return fallback
    try:
        eligible = regime_series.loc[regime_series.index <= date]
        if not eligible.empty:
            value = str(eligible.iloc[-1])
            return value if value in {"BULL", "BEAR", "SIDEWAYS"} else fallback
    except Exception:
        pass
    return fallback


def build_signal_at(
    ticker: str,
    data: pd.DataFrame,
    i: int,
    market_regime: str,
    val_threshold_pct: float = 1.5,
    atr_multiplier: float = 1.5,
    min_rr: float = 1.5,
) -> Optional[dict]:
    """Create a signal using data through bar i only. Targets/stops are known at signal close."""
    if i < 220 or i >= len(data):
        return None
    row = data.iloc[i]
    prev = data.iloc[i - 1]
    cols = ["Close", "High", "Low", "EMA_20", "EMA_50", "EMA_200", "EMA50_Slope",
            "ATR", "Vol_SMA", "Volume", "RSI", "ADX", "BB_WIDTH_PCTL",
            "PRIOR_20_HIGH", "PRIOR_20_LOW", "ROC_20"]
    if any(pd.isna(row.get(c)) for c in cols):
        return None
    close, atr = float(row["Close"]), float(row["ATR"])
    if close <= 0 or atr <= 0:
        return None
    # The volume profile is built from the 20 bars ending before the signal bar.
    poc, val, vah = calculate_volume_profile(data.iloc[:i + 1], 20)
    if poc is None or val is None or vah is None or val <= 0 or vah <= val:
        return None
    volume_ratio = float(row["Volume"] / row["Vol_SMA"]) if row["Vol_SMA"] > 0 else 0
    ema20, ema50, ema200 = map(float, [row["EMA_20"], row["EMA_50"], row["EMA_200"]])
    rsi, adx = float(row["RSI"]), float(row["ADX"])
    direction, setup = None, None
    entry = close
    stop = target = None
    # BULL engine: trend continuation via pullback reclaim or confirmed range breakout.
    if market_regime == "BULL":
        pullback_reclaim = (
            ema20 > ema50 > ema200 and float(row["EMA50_Slope"]) > 0
            and float(row["Low"]) <= ema20 + 0.25 * atr and close > ema20
            and 48 <= rsi <= 72 and volume_ratio >= 0.85
        )
        breakout = (
            ema20 > ema50 > ema200 and close > float(row["PRIOR_20_HIGH"])
            and volume_ratio >= 1.20 and rsi >= 55
        )
        if pullback_reclaim:
            direction, setup = "LONG", "Bull Pullback Reclaim"
        elif breakout:
            direction, setup = "LONG", "Bull 20D Breakout"
        if direction:
            stop = min(entry - atr_multiplier * atr, val - 0.15 * atr)
            risk = entry - stop
            swing_target = float(row["PRIOR_20_HIGH"]) + 1.5 * atr if setup == "Bull Pullback Reclaim" else entry + 2.0 * atr
            target = max(entry + min_rr * risk, min(entry + 2.5 * risk, swing_target))
    # BEAR engine: short-side breakdown/retest. Cash-equity overnight shorts are not assumed available.
    elif market_regime == "BEAR":
        breakdown = (
            ema20 < ema50 < ema200 and float(row["EMA50_Slope"]) < 0
            and close < float(row["PRIOR_20_LOW"]) and volume_ratio >= 1.15 and rsi <= 48
        )
        retest_reject = (
            ema20 < ema50 < ema200 and float(row["High"]) >= ema20 - 0.20 * atr
            and close < ema20 and close < float(prev["Close"]) and 30 <= rsi <= 55
            and volume_ratio >= 0.80
        )
        if breakdown:
            direction, setup = "SHORT", "Bear 20D Breakdown"
        elif retest_reject:
            direction, setup = "SHORT", "Bear EMA20 Rejection"
        if direction:
            stop = max(entry + atr_multiplier * atr, vah + 0.15 * atr)
            risk = stop - entry
            swing_target = max(0.01, float(row["PRIOR_20_LOW"]) - 1.5 * atr)
            target = min(entry - min_rr * risk, max(entry - 2.5 * risk, swing_target))
    # SIDEWAYS engine: range-edge reversals, failed breakdowns and volatility expansion.
    elif market_regime == "SIDEWAYS":
        near_val = (float(row["Low"]) <= val + 0.35 * atr) and ((close - val) / val * 100 <= val_threshold_pct)
        near_vah = float(row["High"]) >= vah - 0.35 * atr
        val_reclaim = near_val and close > val and close > float(row["Open"]) and rsi >= float(prev["RSI"]) and rsi <= 58
        failed_breakdown = float(row["Low"]) < val and close > val and close > float(row["Open"]) and rsi > float(prev["RSI"])
        vah_rejection = near_vah and close < vah and close < float(row["Open"]) and rsi <= float(prev["RSI"]) and rsi >= 42
        squeeze_up = (
            float(row["BB_WIDTH_PCTL"]) <= 0.20 and close > float(row["PRIOR_20_HIGH"])
            and volume_ratio >= 1.25 and rsi >= 55
        )
        squeeze_down = (
            float(row["BB_WIDTH_PCTL"]) <= 0.20 and close < float(row["PRIOR_20_LOW"])
            and volume_ratio >= 1.25 and rsi <= 45
        )
        if failed_breakdown:
            direction, setup = "LONG", "Sideways Failed Breakdown"
        elif val_reclaim:
            direction, setup = "LONG", "Sideways VAL Bounce"
        elif vah_rejection:
            direction, setup = "SHORT", "Sideways VAH Rejection"
        elif squeeze_up:
            direction, setup = "LONG", "Sideways Squeeze Breakout"
        elif squeeze_down:
            direction, setup = "SHORT", "Sideways Squeeze Breakdown"
        if direction == "LONG":
            stop = min(entry - atr_multiplier * atr, val - 0.10 * atr)
            risk = entry - stop
            range_target = vah if vah > entry else entry + 1.8 * risk
            target = min(range_target, entry + 2.5 * risk)
        elif direction == "SHORT":
            stop = max(entry + atr_multiplier * atr, vah + 0.10 * atr)
            risk = stop - entry
            range_target = val if val < entry else entry - 1.8 * risk
            target = max(range_target, entry - 2.5 * risk)
    if direction is None or stop is None or target is None:
        return None
    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr = reward / risk if risk > 0 else 0
    if risk <= 0 or rr < min_rr or target <= 0:
        return None
    return {
        "Date": pd.Timestamp(data.index[i]).strftime("%Y-%m-%d"),
        "Stock": ticker.replace(".NS", ""),
        "TradingView Link": f"https://in.tradingview.com/chart/?symbol=NSE:{ticker.replace('.NS', '')}",
        "Market Regime": market_regime,
        "Strategy": setup,
        "Direction": direction,
        "Entry Price (₹)": round(entry, 2),
        "Target (₹)": round(target, 2),
        "Stop Loss (₹)": round(stop, 2),
        "R:R Ratio": round(rr, 2),
        "ATR (%)": round(float(row["ATR_PCT"]), 2),
        "ADX": round(adx, 1),
        "RSI": round(rsi, 1),
        "Volume Ratio": round(volume_ratio, 2),
        "POC (₹)": round(float(poc), 2),
        "VAL (₹)": round(float(val), 2),
        "VAH (₹)": round(float(vah), 2),
        "_entry": entry, "_target": target, "_stop": stop,
    }


def historical_time_to_target(
    ticker: str,
    data: pd.DataFrame,
    current_signal: dict,
    regime_series: Optional[pd.Series],
    lookback_bars: int = 756,
    max_holding_days: int = 30,
    min_samples: int = 15,
    val_threshold_pct: float = 1.5,
    atr_multiplier: float = 1.5,
    min_rr: float = 1.5,
) -> dict:
    """Empirical analogue estimate using only earlier signals of same setup/direction/regime."""
    n = len(data)
    current_date = pd.Timestamp(data.index[-1])
    start = max(220, n - lookback_bars - max_holding_days)
    durations, outcomes = [], []
    last_sample_i = -max_holding_days
    setup, direction, regime = current_signal["Strategy"], current_signal["Direction"], current_signal["Market Regime"]
    # Sample past signals, never the current signal; future bars are used only to label historical outcomes.
    for i in range(start, max(start, n - max_holding_days - 1)):
        date_i = pd.Timestamp(data.index[i])
        if date_i >= current_date:
            break
        if i - last_sample_i <= max_holding_days:
            continue
        hist_regime = regime_for_date(regime_series, date_i, "SIDEWAYS")
        candidate = build_signal_at(ticker, data, i, hist_regime, val_threshold_pct, atr_multiplier, min_rr)
        if not candidate or candidate["Strategy"] != setup or candidate["Direction"] != direction:
            continue
        last_sample_i = i
        entry, target, stop = candidate["_entry"], candidate["_target"], candidate["_stop"]
        outcome, days = "CENSORED", None
        for j in range(i + 1, min(i + max_holding_days + 1, n)):
            bar = data.iloc[j]
            op, hi, lo = float(bar["Open"]), float(bar["High"]), float(bar["Low"])
            if direction == "LONG":
                if op <= stop:
                    outcome = "STOP"; break
                if op >= target:
                    outcome, days = "TARGET", j - i; break
                if lo <= stop:
                    outcome = "STOP"; break
                if hi >= target:
                    outcome, days = "TARGET", j - i; break
            else:
                if op >= stop:
                    outcome = "STOP"; break
                if op <= target:
                    outcome, days = "TARGET", j - i; break
                if hi >= stop:
                    outcome = "STOP"; break
                if lo <= target:
                    outcome, days = "TARGET", j - i; break
        # A setup that reaches neither barrier within the horizon is a TIMEOUT,
        # and counts as a non-target outcome rather than being silently discarded.
        outcomes.append(outcome if outcome in {"TARGET", "STOP"} else "TIMEOUT")
        if outcome == "TARGET":
            durations.append(days)
    sample_n = len(outcomes)
    if sample_n < min_samples:
        return {
            "Target-before-stop ≤30D (%)": np.nan, "Est. Days (Median)": "Insufficient data",
            "Est. Days (75th pct)": "Insufficient data", "Analogue Samples": sample_n,
            "Time Estimate Status": f"Insufficient sample (<{min_samples})",
        }
    return {
        "Target-before-stop ≤30D (%)": round(outcomes.count("TARGET") / sample_n * 100, 1),
        "Est. Days (Median)": int(np.median(durations)) if durations else "No target hits",
        "Est. Days (75th pct)": int(np.percentile(durations, 75)) if durations else "No target hits",
        "Analogue Samples": sample_n,
        "Time Estimate Status": "Historical analogue estimate" if durations else "No successful analogues",
    }


def scan_one_ticker(
    ticker: str, df: pd.DataFrame, val_threshold_pct: float,
    atr_multiplier: float, min_rr: float, regime_series: Optional[pd.Series] = None,
):
    if df.empty or len(df) < 260:
        return None
    data = add_v3_indicators(df)
    current_date = pd.Timestamp(data.index[-1])
    regime = regime_for_date(regime_series, current_date, "SIDEWAYS")
    signal = build_signal_at(ticker, data, len(data) - 1, regime, val_threshold_pct, atr_multiplier, min_rr)
    if not signal:
        return None
    estimate = historical_time_to_target(
        ticker, data, signal, regime_series,
        val_threshold_pct=val_threshold_pct,
        atr_multiplier=atr_multiplier,
        min_rr=min_rr,
    )
    signal.update(estimate)
    signal.pop("_entry", None); signal.pop("_target", None); signal.pop("_stop", None)
    return signal


@st.cache_data(ttl=20 * 60, show_spinner=False)
def run_live_scan(ticker_tuple: Tuple[str, ...], val_threshold_pct=1.5, atr_multiplier=1.5, min_rr=1.5):
    rows = []
    tickers = list(ticker_tuple)
    start_date = (datetime.now() - timedelta(days=1500)).strftime("%Y-%m-%d")
    # Broad-market regime is derived from Nifty 50, not inferred from each stock.
    current_regime, regime_date = "UNAVAILABLE", "Unavailable"
    try:
        index_raw = yf.download("^NSEI", start=start_date, interval="1d", auto_adjust=False, progress=False, threads=False)
        index_frame = extract_ticker_frame(index_raw, "^NSEI", 1)
        market_regimes = build_market_regime_series(index_frame)
        if not market_regimes.empty:
            current_regime = str(market_regimes.iloc[-1])
            regime_date = pd.Timestamp(market_regimes.index[-1]).strftime("%Y-%m-%d")
    except Exception:
        market_regimes = pd.Series(dtype="object")
    for chunk in iter_chunks(tickers, 40):
        raw = download_price_batch(tuple(chunk), start_date)
        for ticker in chunk:
            try:
                frame = extract_ticker_frame(raw, ticker, len(chunk))
                signal = scan_one_ticker(ticker, frame, val_threshold_pct, atr_multiplier, min_rr, market_regimes)
                if signal:
                    rows.append(signal)
            except Exception:
                continue
    result = pd.DataFrame(rows)
    result.attrs["current_market_regime"] = current_regime
    result.attrs["regime_date"] = regime_date
    return result


# ============================================================
# V3.0 BACKTEST ENGINE — regime-aware long/short simulation
# ============================================================
def simulate_backtest(
    ticker: str,
    frame: pd.DataFrame,
    test_start: pd.Timestamp,
    val_threshold_pct: float = 1.5,
    atr_multiplier: float = 1.5,
    min_rr: float = 1.5,
    initial_capital: float = 100000,
    regime_series: Optional[pd.Series] = None,
    round_trip_cost_pct: float = 0.15,
    max_holding_days: int = 30,
) -> pd.DataFrame:
    """Sequential one-position-per-ticker simulation; signal at close, exits from next bar.
    Conservative stop-first rule if stop and target both touch in the same daily candle.
    """
    if frame.empty or len(frame) < 260:
        return pd.DataFrame()
    df = add_v3_indicators(frame)
    test_start = pd.Timestamp(test_start)
    if test_start.tzinfo is not None:
        test_start = test_start.tz_localize(None)
    trades, capital = [], float(initial_capital)
    i, last_idx = 220, len(df) - 1
    while i < last_idx:
        signal_date = pd.Timestamp(df.index[i])
        if signal_date < test_start:
            i += 1
            continue
        market_regime = regime_for_date(regime_series, signal_date, "SIDEWAYS")
        signal = build_signal_at(ticker, df, i, market_regime, val_threshold_pct, atr_multiplier, min_rr)
        if not signal:
            i += 1
            continue
        direction = signal["Direction"]
        entry, target, stop = signal["_entry"], signal["_target"], signal["_stop"]
        exit_idx, exit_price, exit_type = None, None, None
        for j in range(i + 1, min(last_idx + 1, i + max_holding_days + 1)):
            bar = df.iloc[j]
            op, hi, lo = float(bar["Open"]), float(bar["High"]), float(bar["Low"])
            if direction == "LONG":
                if op <= stop:
                    exit_idx, exit_price, exit_type = j, op, "SL Hit"
                    break
                if op >= target:
                    exit_idx, exit_price, exit_type = j, target, "Target Hit"
                    break
                hit_stop, hit_target = lo <= stop, hi >= target
            else:
                if op >= stop:
                    exit_idx, exit_price, exit_type = j, op, "SL Hit"
                    break
                if op <= target:
                    exit_idx, exit_price, exit_type = j, target, "Target Hit"
                    break
                hit_stop, hit_target = hi >= stop, lo <= target
            if hit_stop:
                exit_idx, exit_price, exit_type = j, stop, "SL Hit"
                break
            if hit_target:
                exit_idx, exit_price, exit_type = j, target, "Target Hit"
                break
        if exit_idx is None:
            # Time stop: close after the configured maximum holding period, or mark open at dataset end.
            candidate_idx = min(i + max_holding_days, last_idx)
            if candidate_idx < last_idx:
                exit_idx = candidate_idx
                exit_price = float(df.iloc[exit_idx]["Close"])
                exit_type = "Time Exit"
            else:
                exit_idx = last_idx
                exit_price = float(df.iloc[last_idx]["Close"])
                exit_type = "Open at End"
        exit_date = pd.Timestamp(df.index[exit_idx])
        gross_return = ((float(exit_price) - entry) / entry * 100) if direction == "LONG" else ((entry - float(exit_price)) / entry * 100)
        net_return = gross_return - float(round_trip_cost_pct)
        pnl_rs = capital * net_return / 100
        if exit_type != "Open at End":
            capital += pnl_rs
        trades.append({
            "Stock": ticker.replace(".NS", ""),
            "Signal Date": signal_date.strftime("%Y-%m-%d"),
            "Entry Date": signal_date.strftime("%Y-%m-%d"),
            "Exit Date": exit_date.strftime("%Y-%m-%d"),
            "Year": str(exit_date.year),
            "Market Regime": market_regime,
            "Strategy": signal["Strategy"],
            "Direction": direction,
            "Type": exit_type,
            "Entry (₹)": round(entry, 2), "Exit (₹)": round(float(exit_price), 2),
            "Target (₹)": round(target, 2), "Stop Loss (₹)": round(stop, 2),
            "R:R at Entry": round(signal["R:R Ratio"], 2),
            "Holding Days": int(exit_idx - i),
            "Gross PnL (%)": round(gross_return, 3),
            "Costs (%)": round(float(round_trip_cost_pct), 3),
            "PnL (%)": round(net_return, 3),
            "Profit/Loss (₹)": round(pnl_rs, 2),
            "Portfolio (₹)": round(capital, 2),
        })
        if exit_type == "Open at End":
            break
        i = exit_idx + 1
    return pd.DataFrame(trades)



@st.cache_data(ttl=60 * 60, show_spinner=False)
def download_market_regimes(start_date: str) -> pd.Series:
    raw = yf.download("^NSEI", start=start_date, interval="1d", auto_adjust=False, progress=False, threads=False)
    frame = extract_ticker_frame(raw, "^NSEI", 1)
    return build_market_regime_series(frame)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def run_backtest_single(ticker: str, years=3, val_threshold_pct=1.5, atr_multiplier=1.5,
                        min_rr=1.5, initial_capital=100000, round_trip_cost_pct=0.15):
    test_start = pd.Timestamp(datetime.now().date() - timedelta(days=int(years * 365.25)))
    warmup_start = test_start - pd.Timedelta(days=500)
    raw = download_price_batch((ticker,), warmup_start.strftime("%Y-%m-%d"))
    frame = extract_ticker_frame(raw, ticker, 1)
    if frame.empty:
        return None, None
    try:
        market_regimes = download_market_regimes(warmup_start.strftime("%Y-%m-%d"))
    except Exception:
        market_regimes = pd.Series(dtype="object")
    trades = simulate_backtest(
        ticker, frame, test_start, val_threshold_pct, atr_multiplier, min_rr,
        initial_capital, market_regimes, round_trip_cost_pct
    )
    return trades, frame


def run_universe_backtest(universe_name: str, years=3, val_threshold_pct=1.5,
                          atr_multiplier=1.5, min_rr=1.5, initial_capital=100000,
                          round_trip_cost_pct=0.15):
    tickers = UNIVERSE_MAP.get(universe_name, UNIVERSE_MAP["Nifty 100"])
    test_start = pd.Timestamp(datetime.now().date() - timedelta(days=int(years * 365.25)))
    warmup_start = (test_start - pd.Timedelta(days=500)).strftime("%Y-%m-%d")
    try:
        market_regimes = download_market_regimes(warmup_start)
    except Exception:
        market_regimes = pd.Series(dtype="object")
    summaries, trades_all, failures = [], [], []
    chunks = list(iter_chunks(tickers, 35))
    progress = st.progress(0, text="Downloading and testing constituent stocks...")
    total_chunks = max(1, len(chunks))
    for chunk_no, chunk in enumerate(chunks, start=1):
        try:
            raw = download_price_batch(tuple(chunk), warmup_start)
        except Exception:
            raw = pd.DataFrame()
        for ticker in chunk:
            try:
                frame = extract_ticker_frame(raw, ticker, len(chunk))
                if frame.empty:
                    failures.append(ticker)
                    continue
                trades = simulate_backtest(
                    ticker, frame, test_start, val_threshold_pct, atr_multiplier, min_rr,
                    initial_capital, market_regimes, round_trip_cost_pct
                )
                if trades.empty:
                    continue
                trades_all.append(trades)
                closed = trades[trades["Type"] != "Open at End"]
                target_hits = int((closed["Type"] == "Target Hit").sum())
                stop_hits = int((closed["Type"] == "SL Hit").sum())
                profitable = int((closed["PnL (%)"] > 0).sum())
                total_closed = len(closed)
                net = float(closed["Profit/Loss (₹)"].sum()) if not closed.empty else 0.0
                summaries.append({
                    "Stock": ticker.replace(".NS", ""),
                    "Completed Trades": total_closed,
                    "Target Hits": target_hits, "Stop Hits": stop_hits,
                    "Time Exits": int((closed["Type"] == "Time Exit").sum()),
                    "Win Rate (%)": round(profitable / total_closed * 100, 1) if total_closed else np.nan,
                    "Net P&L on ₹1L per-stock sequence (₹)": round(net, 2),
                    "Net Trade Return (%)": round(float(closed["PnL (%)"].sum()), 2) if not closed.empty else 0.0,
                    "Open at End": int((trades["Type"] == "Open at End").sum()),
                })
            except Exception:
                failures.append(ticker)
        progress.progress(chunk_no / total_chunks, text=f"Processed batch {chunk_no}/{total_chunks} · {min(chunk_no * 35, len(tickers))}/{len(tickers)} symbols")
    progress.empty()
    summary_df = pd.DataFrame(summaries)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(["Win Rate (%)", "Completed Trades"], ascending=[False, False], na_position="last")
    combined = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()
    summary_df.attrs["failed_tickers"] = failures
    summary_df.attrs["test_start"] = test_start.strftime("%Y-%m-%d")
    return summary_df, combined


# ============================================================
# EXCEL EXPORTS
# ============================================================
def make_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            (frame if frame is not None else pd.DataFrame()).to_excel(writer, index=False, sheet_name=name[:31])
    output.seek(0)
    return output.getvalue()

# ============================================================
# NEWS FEED
# ============================================================
@st.cache_data(ttl=30 * 60, show_spinner=False)
def fetch_breaking_news():
    items = []
    feeds = [
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms",
    ]
    for url in feeds:
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for item in root.findall(".//item")[:6]:
                title_node, desc_node, link_node = item.find("title"), item.find("description"), item.find("link")
                title = title_node.text.strip() if title_node is not None and title_node.text else "Market update"
                desc = desc_node.text if desc_node is not None and desc_node.text else ""
                clean_desc = re.sub(r"<[^>]+>", " ", desc)
                clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                text_blob = (title + " " + clean_desc).lower()
                sentiment, badge = "NEUTRAL", "badge-neutral"
                if any(w in text_blob for w in ["profit", "surges", "jumps", "rally", "record high", "growth", "beats estimates"]):
                    sentiment, badge = "BULLISH", "badge-bull"
                elif any(w in text_blob for w in ["falls", "slumps", "loss", "crash", "war", "inflation", "cuts guidance", "downgrade"]):
                    sentiment, badge = "BEARISH", "badge-bear"
                impacts = []
                if "bank" in text_blob: impacts.append("Banking: HDFCBANK, ICICIBANK, SBIN")
                if any(w in text_blob for w in ["technology", "software", "it sector"]): impacts.append("IT: TCS, INFY, HCLTECH")
                if "auto" in text_blob: impacts.append("Auto: MARUTI, M&M, TATAMOTORS")
                if any(w in text_blob for w in ["oil", "crude"]): impacts.append("Energy: RELIANCE, ONGC, BPCL")
                items.append({
                    "title": title, "description": (clean_desc[:260] + ("…" if len(clean_desc) > 260 else "")),
                    "sentiment": sentiment, "badge": badge,
                    "impact": ", ".join(impacts) if impacts else "Broad market / sector impact; verify independently",
                    "link": link_node.text.strip() if link_node is not None and link_node.text else "",
                })
        except Exception:
            continue
    # Avoid duplicate headlines across feeds.
    unique, seen = [], set()
    for item in items:
        key = item["title"].lower()
        if key not in seen:
            unique.append(item); seen.add(key)
    return unique

# ============================================================
# HEADER + INDEX SNAPSHOT
# ============================================================
st.title("⚡ Nifty Multi-Universe Quant Terminal")
st.caption("V3.0 · Market-regime-aware Bull / Bear / Sideways trading engines · Empirical target-time estimates")

try:
    index_data = yf.download(["^NSEI", "^NSEBANK"], period="5d", interval="1d", progress=False, auto_adjust=False, threads=False)
    if not index_data.empty and isinstance(index_data.columns, pd.MultiIndex):
        close_frame = index_data["Close"] if "Close" in index_data.columns.get_level_values(0) else index_data.xs("Close", axis=1, level=1)
        c1, c2 = st.columns(2)
        for col, symbol, label in [(c1, "^NSEI", "NIFTY 50"), (c2, "^NSEBANK", "BANK NIFTY")]:
            if symbol in close_frame.columns:
                series = close_frame[symbol].dropna()
                if len(series) >= 2:
                    change = (series.iloc[-1] / series.iloc[-2] - 1) * 100
                    col.metric(label, f"{series.iloc[-1]:,.2f}", f"{change:+.2f}%")
except Exception:
    st.caption("Live index snapshot temporarily unavailable.")

with st.expander("Universe data status", expanded=False):
    for universe_name, message in UNIVERSE_STATUS.items():
        st.write(f"**{universe_name}:** {message}")
    st.caption("Current constituent lists are used for historical scans. This introduces survivorship bias in multi-year backtests; historical point-in-time membership is not available in this version.")

st.divider()
tab1, tab2, tab3 = st.tabs(["🚀 Live Multi-Universe Scanner", "📊 Universe Strategy Backtester", "📰 Market News & Impact Analysis"])

# ============================================================
# TAB 1 - LIVE SCANNER
# ============================================================
with tab1:
    st.subheader("V3.0 Multi-Regime Scanner Engine")
    st.caption("Bull: trend pullbacks / breakouts · Bear: breakdowns / retest rejections · Sideways: VAL/VAH reversals, failed breakdowns and squeeze expansions.")
    c1, c2 = st.columns([1, 2])
    selected_universe = c1.selectbox("Select Index Universe", list(UNIVERSE_MAP), index=1, key="live_universe")
    reset_live = c2.checkbox("Use V3 baseline parameters (VAL 1.5%, ATR 1.5x, R:R 1.5)", value=True, key="live_reset")
    d_val = 1.5 if reset_live else 2.5
    d_atr = 1.5
    d_rr = 1.5
    p1, p2, p3 = st.columns(3)
    val_limit = p1.slider("VAL Distance Threshold (%)", 0.5, 5.0, d_val, 0.5, key="live_val")
    atr_mult = p2.slider("ATR Stop Buffer Multiplier", 0.8, 2.5, d_atr, 0.1, key="live_atr")
    rr_min = p3.slider("Minimum R:R Ratio", 0.8, 2.0, d_rr, 0.1, key="live_rr")
    tickers = UNIVERSE_MAP[selected_universe]
    st.caption(f"Universe size: {len(tickers)} symbols · Scan uses daily data and may take several minutes for larger universes.")
    if st.button("🔍 Run Live Scan", type="primary", key="run_live"):
        with st.spinner(f"Scanning {len(tickers)} stocks in {selected_universe}..."):
            results = run_live_scan(tuple(tickers), val_limit, atr_mult, rr_min)
        st.session_state["live_scan_results"] = results
        st.session_state["live_scan_universe"] = selected_universe
    results = st.session_state.get("live_scan_results", pd.DataFrame())
    if isinstance(results, pd.DataFrame) and not results.empty:
        current_regime = results.attrs.get("current_market_regime", "Unavailable")
        regime_date = results.attrs.get("regime_date", "Unavailable")
        st.metric("Current Nifty 50 Market Regime", current_regime, f"as of {regime_date}")
        st.success(f"Found {len(results)} potential setups in {st.session_state.get('live_scan_universe', selected_universe)}.")
        st.caption("Target-before-stop probability within 30 sessions and estimated days use historical same-stock/same-setup analogues. These are conditional estimates, not guarantees; low sample counts are explicitly withheld. SHORT setups require an eligible instrument and are not instructions to short cash equities overnight.")
        st.dataframe(results, column_config={"TradingView Link": st.column_config.LinkColumn("TradingView Chart", display_text="📊 Open Chart")}, use_container_width=True, hide_index=True)
        st.download_button("📥 Export Scan to Excel", make_excel_bytes({"LiveSetups": results}), f"{selected_universe}_Scan_{datetime.now():%Y%m%d}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif "live_scan_results" in st.session_state:
        empty_results = st.session_state.get("live_scan_results")
        if isinstance(empty_results, pd.DataFrame):
            st.metric("Current Nifty 50 Market Regime", empty_results.attrs.get("current_market_regime", "Unavailable"),
                      f"as of {empty_results.attrs.get('regime_date', 'Unavailable')}")
        st.info("No setups matched the selected parameters. This is a valid no-trade result; do not force entries just to increase signal count.")
    else:
        st.info("Choose your parameters and run a scan. The app does not scan automatically on every page refresh.")

# ============================================================
# TAB 2 - BACKTESTER
# ============================================================
with tab2:
    st.subheader("Multi-Stock & Index Backtester")
    mode = st.radio("Backtest Mode", ["Single Stock", "Scan Entire Index Universe"], horizontal=True)
    reset_bt = st.checkbox("Use baseline backtest parameters (VAL 1.0%, ATR 1.2x, R:R 1.0)", value=True, key="bt_reset")
    bt_val_default = 1.5 if reset_bt else 2.5
    bt_atr_default, bt_rr_default = 1.5, 1.5
    if mode == "Single Stock":
        cols = st.columns(6)
        ticker_options = sorted(UNIVERSE_MAP["Nifty 500"])
        default_ticker = ticker_options.index("RELIANCE.NS") if "RELIANCE.NS" in ticker_options else 0
        symbol = cols[0].selectbox("Stock Ticker", ticker_options, index=default_ticker)
        capital = cols[1].number_input("Starting Capital (₹)", min_value=1000, value=100000, step=10000)
        years = cols[2].slider("Period (years)", 1, 10, 5)
        threshold = cols[3].slider("VAL %", 0.5, 5.0, bt_val_default, 0.5, key="single_val")
        atr_value = cols[4].slider("ATR Mult", 0.8, 2.5, bt_atr_default, 0.1, key="single_atr")
        rr_value = cols[5].slider("Min R:R", 0.8, 2.0, bt_rr_default, 0.1, key="single_rr")
        if st.button("▶️ Run Single Stock Backtest", type="primary"):
            with st.spinner(f"Downloading and simulating {symbol}..."):
                trade_df, price_df = run_backtest_single(symbol, years, threshold, atr_value, rr_value, capital)
            st.session_state["single_backtest"] = (trade_df, symbol, capital, years)
        saved = st.session_state.get("single_backtest")
        if saved:
            trade_df, saved_symbol, starting_capital, saved_years = saved
            if trade_df is not None and not trade_df.empty:
                closed = trade_df[trade_df["Type"] != "Open at End"]
                wins = int((closed["Type"] == "Target Hit").sum())
                losses = int((closed["Type"] == "SL Hit").sum())
                count = len(closed)
                profitable_closed = int((closed["PnL (%)"] > 0).sum())
                final_capital = float(closed["Portfolio (₹)"].iloc[-1]) if not closed.empty else float(starting_capital)
                net = final_capital - float(starting_capital)
                win_rate = profitable_closed / count * 100 if count else 0
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Starting Capital", f"₹{starting_capital:,.0f}")
                m2.metric("Realised Capital", f"₹{final_capital:,.2f}", f"{net:+,.2f}")
                m3.metric("Realised P&L", f"₹{net:,.2f}")
                m4.metric("Closed-Trade Win Rate", f"{win_rate:.1f}% ({profitable_closed} profitable / {count} closed)")
                open_rows = trade_df[trade_df["Type"] == "Open at End"]
                if not open_rows.empty:
                    st.warning("One position remained open at the end of the test. It is marked to market in the trade log and excluded from closed-trade win rate and realised capital.")
                st.markdown("### 📅 Yearly Performance")
                yearly = closed.groupby("Year", sort=True) if not closed.empty else []
                if len(yearly):
                    year_cols = st.columns(min(len(yearly), 5))
                    for idx, (year, group) in enumerate(yearly):
                        yw = int((group["Type"] == "Target Hit").sum())
                        yl = int((group["Type"] == "SL Hit").sum())
                        total = len(group)
                        yr = (group["PnL (%)"] > 0).sum() / total * 100 if total else 0
                        year_cols[idx % len(year_cols)].metric(str(year), f"{yr:.1f}% profitable", f"{yw} target / {yl} stops · {group['PnL (%)'].sum():+.1f}%")
                if not closed.empty:
                    curve = closed[["Exit Date", "Portfolio (₹)"]].copy()
                    curve["Exit Date"] = pd.to_datetime(curve["Exit Date"])
                    fig = go.Figure(go.Scatter(x=curve["Exit Date"], y=curve["Portfolio (₹)"], mode="lines+markers", line=dict(color="#00E5FF", width=3)))
                    fig.update_layout(title=f"{saved_symbol} Realised Capital Curve", template="plotly_dark", xaxis_title="Exit date", yaxis_title="Capital (₹)")
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(trade_df, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Trade Log", make_excel_bytes({"Trades": trade_df, "Closed Trades": closed}), f"{saved_symbol}_Backtest_{saved_years}Y.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No qualifying trades were generated for this ticker and period.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        universe = c1.selectbox("Index Universe", list(UNIVERSE_MAP), index=3)
        years = c2.slider("Lookback Period (years)", 1, 10, 5)
        capital = c3.number_input("Starting Capital per Stock (₹)", min_value=1000, value=100000, step=10000)
        threshold = c4.slider("VAL Distance (%)", 0.5, 5.0, bt_val_default, 0.5, key="univ_val")
        atr_value, rr_value = st.columns(2)
        atr_mult_univ = atr_value.slider("ATR Stop Multiplier", 0.8, 2.5, bt_atr_default, 0.1, key="univ_atr")
        rr_univ = rr_value.slider("Minimum R:R", 0.8, 2.0, bt_rr_default, 0.1, key="univ_rr")
        st.caption("Universe results are independent per-stock trade sequences, not a single pooled portfolio. Capital is reset separately for each stock; do not add final values together as if all trades were executed concurrently.")
        if st.button(f"▶️ Run {universe} Universe Backtest", type="primary"):
            with st.spinner(f"Backtesting {len(UNIVERSE_MAP[universe])} symbols over {years} years. This can take several minutes..."):
                summary, all_trades = run_universe_backtest(universe, years, threshold, atr_mult_univ, rr_univ, capital)
            st.session_state["universe_backtest"] = (summary, all_trades, universe, years)
        saved_universe = st.session_state.get("universe_backtest")
        if saved_universe:
            summary, all_trades, saved_name, saved_years = saved_universe
            if not summary.empty:
                st.success(f"Backtest complete: qualifying trades found in {len(summary)} stocks.")
                if not all_trades.empty:
                    closed = all_trades[all_trades["Type"] != "Open at End"]
                    wins = int((closed["Type"] == "Target Hit").sum())
                    losses = int((closed["Type"] == "SL Hit").sum())
                    total = wins + losses
                    win_rate = wins / total * 100 if total else 0
                    n1, n2, n3, n4 = st.columns(4)
                    n1.metric("Completed Trades", f"{total:,}")
                    n2.metric("Wins / Losses", f"{wins:,} / {losses:,}")
                    n3.metric("Win Rate", f"{win_rate:.1f}%")
                    n4.metric("Stocks with Signals", f"{len(summary):,}")
                    st.markdown("### 📅 Universe-wide Yearly Breakdown")
                    if not closed.empty:
                        yearly = closed.groupby("Year", sort=True)
                        year_cols = st.columns(min(len(yearly), 5))
                        for idx, (year, group) in enumerate(yearly):
                            yw = int((group["Type"] == "Target Hit").sum())
                            yl = int((group["Type"] == "SL Hit").sum())
                            n = yw + yl
                            year_cols[idx % len(year_cols)].metric(str(year), f"{yw / n * 100:.1f}% win" if n else "—", f"{yw}W / {yl}L · {n} trades")
                st.subheader("📌 Stock Performance Summary")
                st.dataframe(summary, use_container_width=True, hide_index=True)
                st.subheader("📜 Complete Trade Execution Log")
                st.dataframe(all_trades, use_container_width=True, hide_index=True)
                failures = summary.attrs.get("failed_tickers", [])
                if failures:
                    st.caption(f"No usable Yahoo Finance data for {len(failures)} symbols. Some symbols may be delisted, renamed, or temporarily unavailable.")
                st.download_button("📥 Export Full Backtest Workbook", make_excel_bytes({"Stock Summary": summary, "All Trades": all_trades, "Closed Trades": all_trades[all_trades["Type"] != "Open at End"] if not all_trades.empty else pd.DataFrame()}), f"{saved_name.replace(' ', '_')}_{saved_years}Y_Backtest.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No qualifying signals were found. Check the universe data status or try a wider VAL threshold / lower R:R.")

# ============================================================
# TAB 3 - NEWS
# ============================================================
with tab3:
    st.subheader("📰 Real-Time Global & Local Financial News")
    st.caption("Rule-based headline sentiment and keyword-based sector mapping. This is not an AI model or investment recommendation.")
    if st.button("🔄 Refresh Market News"):
        fetch_breaking_news.clear()
    news = fetch_breaking_news()
    if news:
        for item in news:
            safe_title = item["title"].replace("<", "&lt;").replace(">", "&gt;")
            safe_desc = item["description"].replace("<", "&lt;").replace(">", "&gt;")
            safe_impact = item["impact"].replace("<", "&lt;").replace(">", "&gt;")
            link_html = f'<a href="{item["link"]}" target="_blank" style="color:#00E5FF">Read source ↗</a>' if item["link"].startswith("http") else ""
            st.markdown(
                f'<div class="news-card"><span class="{item["badge"]}">{item["sentiment"]}</span>'
                f'<h4 style="margin:8px 0;color:#FFFFFF">{safe_title}</h4>'
                f'<p style="color:#94A3B8;font-size:.9rem">{safe_desc}</p>'
                f'<div style="margin-top:8px;font-size:.85rem;color:#00E5FF"><strong>🎯 Possible impact:</strong> {safe_impact}</div>{link_html}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Unable to fetch live news feeds at the moment. Please try refreshing later.")

# ============================================================
# SIDEBAR QUANT NOTES
# ============================================================
with st.sidebar:
    st.header("💬 AI Quant Assistant")
    st.caption("Quick strategy notes (rule-based; no external AI model is connected).")
    query = st.text_input("Enter a stock symbol or question:")
    if query:
        symbol_text = query.strip().upper()
        st.write(f"**Quant notes for `{symbol_text}`**")
        st.info(
            "1. Check the live scanner for price proximity to the prior 20-session volume-profile VAL.\n\n"
            "2. Confirm price is above EMA 200 and volume is at least 80% of its 20-session average.\n\n"
            "3. Review entry, stop, target and R:R; the scanner is a research filter, not a buy/sell instruction.\n\n"
            "4. Validate liquidity, corporate actions, results, broader trend and execution costs independently."
        )
    st.divider()
    st.caption("V3 backtest assumptions: Nifty 50 regime classification; signal at close; next-session exits; conservative stop-first same-bar handling; 0.15% round-trip friction assumption (not a broker-specific fee quote). Short trades are theoretical and require an eligible instrument/strategy; overnight cash-equity shorting is not assumed to be available.")
