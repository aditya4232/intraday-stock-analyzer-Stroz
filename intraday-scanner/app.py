"""
app.py — AI Intraday Trading Scanner (Streamlit Dashboard)
============================================================
Professional intraday stock scanner dashboard for NSE equities.

Architecture:
  - Frontend: Streamlit with custom dark theme (Bloomberg-style)
  - Backend: Graph-pipeline scanner (inspired by ScrapeGraphAI)
  - Data: ScrapeGraphAI-style scraping graph + yfinance for 5-minute intraday data
  - Charts: Plotly candlestick with VWAP + EMA overlays
  - Coverage: Nifty 50 + 200+ extended stocks, categorized by sector

Features:
  - Live auto-refresh (60s) with toggle
  - Sector filter + score/RSI thresholds
  - Nifty 50 / Broader Market toggle
  - Color-coded results table with target/SL and sector info
  - Interactive Plotly charts for selected stock
  - Top 5 picks section
  - Sector breakdown visualization
  - CSV/Excel export
"""

import datetime
import logging

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from config import AUTO_REFRESH_INTERVAL_MS, LOG_LEVEL

logger = logging.getLogger(__name__)

# Attempt import at module level; failure is handled gracefully later
try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Must be the first Streamlit command
st.set_page_config(
    page_title="AI Intraday Scanner",
    page_icon="\U0001F4CA",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Startup / Preflight checks (display helpful warnings when deploying)
# ---------------------------------------------------------------------------
def render_startup_checks() -> None:
    """Display Streamlit warnings or info about missing LLM/API configuration."""
    try:
        # Import scraper helper to inspect LLM/SGAI config
        import scraper as _scraper
        cfg = None
        try:
            cfg = _scraper._build_sgai_config()
        except Exception:
            cfg = None

        # Is scrapegraphai package available?
        try:
            import scrapegraphai  # type: ignore
            _has_sgai_pkg = True
        except Exception:
            _has_sgai_pkg = False

        if cfg is None:
            st.warning(
                "No LLM / ScrapeGraphAI configuration detected. "
                "ScrapeGraphAI features will be disabled and the app will fall back to BeautifulSoup/yfinance. "
                "To enable ScrapeGraphAI, set `SCRAPEGRAPHAI_CLOUD_API_KEY` (sgai-...) or configure `SCRAPE_LLM_PROVIDER`/`SCRAPE_LLM_API_KEY`. "
                "See the README for secure setup instructions."
            )
        else:
            # Config exists; ensure the package is installed for cloud usage
            if not _has_sgai_pkg and (cfg.get("api_key") or cfg.get("llm", {}).get("api_key")):
                st.error(
                    "ScrapeGraphAI configuration found but the `scrapegraphai` package is not installed. "
                    "Install it with `pip install scrapegraphai` or remove cloud config to use the fallback scrapers."
                )
            else:
                st.info("LLM / ScrapeGraphAI configuration detected — enhanced scraping enabled.")

    except Exception:
        # Non-fatal: don't stop the app if checks fail
        return


# Render startup checks (shown above the UI)
render_startup_checks()

# ---------------------------------------------------------------------------
# Custom CSS — Bloomberg Terminal Dark Theme
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    .stApp {
        background-color: #0E0F10;
        color: #E0E0E0;
    }
    [data-testid="stSidebar"] {
        background-color: #1A1A1D;
        border-right: 1px solid #2A2A2D;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #CCCCCC;
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    [data-testid="stMetric"] {
        background-color: #1A1A1D;
        border: 1px solid #2A2A2D;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    [data-testid="stMetric"] label {
        color: #888888 !important;
        font-size: 0.8rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.4rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
    .stButton > button {
        background-color: #2962FF;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #1E88E5;
        box-shadow: 0 4px 12px rgba(41,98,255,0.3);
    }
    .stSelectbox > div > div {
        background-color: #1A1A1D;
        border-color: #2A2A2D;
        color: #E0E0E0;
    }
    [data-testid="stDataFrame"] {
        background-color: transparent;
    }
    [data-testid="stDataFrame"] table {
        font-size: 13px;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1A1A1D;
        border-bottom: 1px solid #2A2A2D;
    }
    .stTabs [data-baseweb="tab"] {
        color: #888888;
    }
    .stTabs [aria-selected="true"] {
        color: #2962FF !important;
        border-bottom-color: #2962FF !important;
    }
    hr {
        border-color: #2A2A2D !important;
        margin: 8px 0 !important;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-open {
        background-color: rgba(0, 200, 83, 0.15);
        color: #00C853;
        border: 1px solid rgba(0, 200, 83, 0.3);
    }
    .status-closed {
        background-color: rgba(255, 82, 82, 0.15);
        color: #FF5252;
        border: 1px solid rgba(255, 82, 82, 0.3);
    }
    .nifty50-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FF6B35, #FF3D00);
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .broader-badge {
        display: inline-block;
        background: #2A2A2D;
        color: #888;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 500;
    }
    .stDownloadButton > button {
        background-color: #2A2A2D;
        color: #E0E0E0;
        border: 1px solid #3A3A3D;
        border-radius: 6px;
        padding: 4px 14px;
        font-size: 0.8rem;
    }
    .stDownloadButton > button:hover {
        background-color: #3A3A3D;
    }
    .stCheckbox > label {
        color: #CCCCCC !important;
    }
    .stSpinner > div {
        border-color: #2962FF !important;
    }
    .stAlert {
        background-color: #1A1A1D !important;
        border: 1px solid #2A2A2D !important;
        color: #E0E0E0 !important;
    }
    .js-plotly-plot, .plot-container {
        width: 100% !important;
    }
    .top-pick-card {
        background: linear-gradient(135deg, #1A1A1D 0%, #222225 100%);
        border: 1px solid #2A2A2D;
        border-radius: 10px;
        padding: 16px;
        margin: 4px 0;
        transition: all 0.2s;
    }
    .top-pick-card:hover {
        border-color: #2962FF;
        box-shadow: 0 4px 16px rgba(41,98,255,0.15);
    }
    .top-pick-symbol {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .top-pick-score {
        font-size: 1.3rem;
        font-weight: 700;
        color: #00E676;
    }
    .top-pick-detail {
        font-size: 0.8rem;
        color: #888888;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Imports (after page config)
# ---------------------------------------------------------------------------
from scanner import scan_stocks, calculate_target_sl, scrape_and_scan
from indicators import (
    calculate_vwap,
    calculate_ema,
)
from stocks_db import get_sectors, get_symbol_count, get_nifty50_count, get_stock_count
from utils import (
    is_market_open,
    get_ist_time,
    fetch_chart_data,
    export_to_csv,
    export_to_excel,
    style_dataframe,
    format_volume,
    get_top_picks,
)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def create_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create a professional candlestick chart with VWAP, EMA5, EMA20, and volume."""
    vwap = calculate_vwap(df)
    ema5 = calculate_ema(df, period=5)
    ema20 = calculate_ema(df, period=20)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price",
            increasing_line_color="#00C853", decreasing_line_color="#FF5252",
            line=dict(width=1),
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=vwap, name="VWAP",
            line=dict(color="#FF6D00", width=1.5, dash="dash"), opacity=0.8,
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema5, name="5 EMA",
            line=dict(color="#448AFF", width=1.5), opacity=0.9,
        ), row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema20, name="20 EMA",
            line=dict(color="#FFAB40", width=1.5), opacity=0.9,
        ), row=1, col=1,
    )

    colors = np.where(df["Close"].values >= df["Open"].values, "#00C853", "#FF5252")
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["Volume"], name="Volume",
            marker_color=colors, opacity=0.6,
        ), row=2, col=1,
    )

    fig.update_layout(
        title=dict(text=f"{symbol} \u2014 Intraday (5min)", font=dict(size=16, color="#FFFFFF"), x=0.02),
        template="plotly_dark", paper_bgcolor="#0E0F10", plot_bgcolor="#151618",
        hovermode="x unified", xaxis_rangeslider_visible=False,
        height=550, margin=dict(l=40, r=20, t=50, b=30),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )
    fig.update_yaxes(title_text="Price (Rs)", row=1, col=1, gridcolor="#2A2A2D")
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor="#2A2A2D")
    fig.update_xaxes(gridcolor="#2A2A2D", row=1, col=1)
    fig.update_xaxes(gridcolor="#2A2A2D", row=2, col=1)

    return fig


def _safe_currency(val) -> str:
    """Format value as currency, handling NaN and non-numeric types."""
    try:
        if pd.isna(val):
            return "N/A"
        return f"Rs{val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "scan_results" not in st.session_state:
    st.session_state.scan_results = pd.DataFrame()
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None
if "sector" not in st.session_state:
    st.session_state.sector = "All Sectors"
if "min_score" not in st.session_state:
    st.session_state.min_score = 0
if "min_rsi" not in st.session_state:
    st.session_state.min_rsi = 0
if "index_filter" not in st.session_state:
    st.session_state.index_filter = "All Stocks"
if "sector_dataframe" not in st.session_state:
    st.session_state.sector_dataframe = pd.DataFrame()

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
if st.session_state.auto_refresh and _HAS_AUTOREFRESH:
    _ = st_autorefresh(interval=AUTO_REFRESH_INTERVAL_MS, key="auto_refresh_timer")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
col_logo, col_title, col_status, col_time, col_refresh = st.columns([0.5, 3, 2, 2, 1.5])

with col_logo:
    st.markdown("### \U0001F4CA")

with col_title:
    st.markdown(
        "<h1 style='margin: 0; font-size: 1.5rem;'>AI Intraday Trading Scanner</h1>"
        "<p style='margin: 0; color: #666; font-size: 0.75rem;'>"
        "NSE Equity Scanner \u00B7 Nifty 50 + 200+ Stocks \u00B7 ScrapeGraphAI Pipeline \u00B7 5min Data</p>",
        unsafe_allow_html=True,
    )

with col_status:
    market_open = is_market_open()
    status_class = "status-open" if market_open else "status-closed"
    status_text = "\u25CF LIVE" if market_open else "\u25CF CLOSED"
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%;'>"
        f"<span class='status-badge {status_class}'>{status_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

with col_time:
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%; color: #888; font-size: 0.85rem;'>"
        f"\U0001F550 {get_ist_time()} IST</div>",
        unsafe_allow_html=True,
    )

with col_refresh:
    refresh_status = "ON" if st.session_state.auto_refresh else "OFF"
    refresh_secs = AUTO_REFRESH_INTERVAL_MS // 1000
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%; color: #888; font-size: 0.75rem;'>"
        f"\U0001F504 Auto: {refresh_status} ({refresh_secs}s)</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin: 8px 0 16px 0;'>", unsafe_allow_html=True)

if not market_open:
    from datetime import timedelta as td
    ist_now = datetime.datetime.now(td(hours=5, minutes=30))
    next_open = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
    if ist_now.hour >= 15 or (ist_now.hour == 15 and ist_now.minute >= 30):
        next_open += td(days=1)
    while next_open.weekday() >= 5:
        next_open += td(days=1)
    hours_until = (next_open - ist_now).total_seconds() / 3600
    st.info(
        f"\U0001F552 Market closed. Next session opens ~{hours_until:.0f}h "
        f"({next_open.strftime('%a %I:%M %p')} IST). "
        "Showing last available data."
    )

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### \u2699\uFE0F Controls")
    st.markdown("---")

    total_db = get_stock_count()
    nifty50_db = get_nifty50_count()
    st.markdown(
        f"<div style='font-size: 0.75rem; color: #666; margin-bottom: 8px;'>"
        f"\U0001F4DA Database: {total_db} stocks \u00B7 {nifty50_db} Nifty 50</div>",
        unsafe_allow_html=True,
    )

    sectors = get_sectors()
    selected_sector = st.selectbox(
        "Sector",
        sectors,
        index=sectors.index(st.session_state.sector) if st.session_state.sector in sectors else 0,
        key="sector_select",
    )

    index_filter = st.selectbox(
        "Index Membership",
        ["All Stocks", "NIFTY 50 Only", "Broader Market Only"],
        index=0,
        help="Filter by Nifty 50 membership or broader market",
    )

    min_score = st.slider(
        "Minimum Score", min_value=0, max_value=10,
        value=st.session_state.min_score, step=1,
        help="Filter stocks by minimum score (0-10). 8+ = BUY, 6-7 = WATCH",
    )

    min_rsi = st.slider(
        "Minimum RSI", min_value=0, max_value=100,
        value=st.session_state.min_rsi, step=5,
        help="Filter stocks by minimum RSI value",
    )

    st.markdown("---")

    _ = st.checkbox(
        "Auto Refresh (every 60s)",
        key="auto_refresh",
        help="Automatically refresh data every 60 seconds",
    )

    scan_clicked = st.button(
        "\U0001F50D Scan Now", type="primary", use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### \U0001F4C8 Legend")
    st.markdown(
        """
        <div style="font-size: 0.8rem; color: #888;">
            <p><span style="color: #00E676; font-weight: bold;">BUY</span> - Score 8-10</p>
            <p><span style="color: #FFD54F; font-weight: bold;">WATCH</span> - Score 6-7</p>
            <p><span style="color: #EF5350; font-weight: bold;">AVOID</span> - Score 0-5</p>
            <p style="margin-top: 8px;">
              <span style="background: linear-gradient(135deg, #FF6B35, #FF3D00); color: white; padding: 1px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700;">NIFTY 50</span>
              - Index constituent
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Market countdown
    if market_open:
        from datetime import datetime as dt, time as tm, timedelta as td
        ist_now = dt.now(td(hours=5, minutes=30))
        close_today = ist_now.replace(hour=15, minute=30, second=0, microsecond=0)
        remaining = close_today - ist_now
        mins_left = int(remaining.total_seconds() // 60)
        st.markdown(
            f"<div style='font-size: 0.75rem; color: #00C853; text-align: center;'>"
            f"\u23F1 Market closes in {mins_left}m</div>",
            unsafe_allow_html=True,
        )
    else:
        from datetime import datetime as dt, time as tm, timedelta as td
        ist_now = dt.now(td(hours=5, minutes=30))
        next_open = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
        if ist_now >= next_open:
            next_open += td(days=1)
        # If weekend, skip to Monday
        while next_open.weekday() >= 5:
            next_open += td(days=1)
        remaining = next_open - ist_now
        hours_left = int(remaining.total_seconds() // 3600)
        st.markdown(
            f"<div style='font-size: 0.75rem; color: #FF5252; text-align: center;'>"
            f"\u23F0 Market opens in ~{hours_left}h</div>",
            unsafe_allow_html=True,
        )

    # Clear cache button
    if st.button("\u267B Clear Cache", help="Clear cached data and force refresh"):
        st.cache_data.clear()
        st.session_state.scan_results = pd.DataFrame()
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 0.7rem; color: #555; text-align: center;'>"
        "Data: yfinance + ScrapeGraphAI<br>"
        "Nifty 50 + 300+ Stocks<br>"
        "v3.0.0</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Update session state
# ---------------------------------------------------------------------------
st.session_state.sector = selected_sector
st.session_state.min_score = min_score
st.session_state.min_rsi = min_rsi
st.session_state.index_filter = index_filter

# ---------------------------------------------------------------------------
# Main Panel — Three Tabs
# ---------------------------------------------------------------------------
tab_scanner, tab_sectors, tab_toppicks = st.tabs([
    "\U0001F4CB Scanner Results",
    "\U0001F3ED Sector Breakdown",
    "\U0001F3C6 Top 5 Picks",
])

with tab_scanner:
    # Auto-trigger scan on first load if data is stale (>5 min old) or empty
    last_scan = st.session_state.last_scan_time
    data_stale = (
        last_scan is None
        or (datetime.datetime.now() - last_scan).total_seconds() > 300
    ) if last_scan else True
    should_scan = scan_clicked or (st.session_state.scan_results.empty and data_stale)

    if should_scan:
        with st.spinner(f"\U0001F50D Scanning {selected_sector} sector..."):
            try:
                scan_output = scrape_and_scan(
                    sector=selected_sector,
                    min_score=min_score,
                    min_rsi=min_rsi,
                )
                results = scan_output["results"]
                st.session_state.scan_results = results
                st.session_state.sector_dataframe = scan_output.get("sector_dataframe", pd.DataFrame())
                st.session_state.last_scan_time = datetime.datetime.now()
            except Exception as e:
                st.error(f"Scan failed: {str(e)}")
                st.session_state.scan_results = pd.DataFrame()

    results = st.session_state.scan_results

    # Apply index filter
    if not results.empty and "Index" in results.columns:
        if index_filter == "NIFTY 50 Only":
            results = results[results["Index"] == "NIFTY 50"]
        elif index_filter == "Broader Market Only":
            results = results[results["Index"] != "NIFTY 50"]

    if not results.empty:
        last_time = st.session_state.last_scan_time
        time_str = last_time.strftime("%I:%M:%S %p") if last_time else "N/A"

        total_stocks = get_symbol_count(selected_sector)
        scanned_count = len(results)
        buy_count = len(results[results["Action"] == "BUY"])
        watch_count = len(results[results["Action"] == "WATCH"])
        avoid_count = scanned_count - buy_count - watch_count

        nifty50_in_results = len(results[results["Index"] == "NIFTY 50"]) if "Index" in results.columns else 0
        broader_in_results = scanned_count - nifty50_in_results

        col_info, col_buy, col_watch, col_avoid = st.columns(4)
        with col_info:
            st.metric("Stocks Scanned", str(total_stocks), f"{scanned_count} passed filters")
        with col_buy:
            st.metric("BUY Signals", buy_count)
        with col_watch:
            st.metric("WATCH Signals", watch_count)
        with col_avoid:
            st.metric("Avoid/Filtered", max(avoid_count, 0))

        st.markdown(
            f"<p style='color: #666; font-size: 0.8rem;'>"
            f"Last scan: {time_str} IST &nbsp;&middot;&nbsp; "
            f"<span class='nifty50-badge'>NIFTY 50: {nifty50_in_results}</span> "
            f"<span class='broader-badge'>Broader: {broader_in_results}</span>"
            f"</p>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No stocks match your criteria. Try lowering the score/RSI filters or select a different sector.")

    if not results.empty:
        # Data freshness indicator
        if "Price Time" in results.columns:
            live_count = len(results[~results["Price Time"].str.contains("Delayed", na=False)])
            delayed_count = len(results) - live_count
            freshness_text = (
                f"<span style='color: #00C853;'>&#9679; Live: {live_count}</span>"
                if live_count > 0 else ""
            )
            delayed_text = (
                f" <span style='color: #FFAB40;'>&#9679; Delayed: {delayed_count}</span>"
                if delayed_count > 0 else ""
            )
            st.markdown(
                f"<p style='color: #888; font-size: 0.75rem; margin-bottom: 4px;'>{freshness_text}{delayed_text}</p>",
                unsafe_allow_html=True,
            )

        st.markdown("### \U0001F4CA Scanner Results")

        display_cols = [
            "Symbol", "Company", "Sector", "Market Cap", "Index",
            "LTP", "Price Time",
            "VWAP", "5EMA", "20EMA",
            "RSI", "Volume", "Score", "Action",
            "Target", "Stoploss",
            "ML Confidence", "Pattern", "Sentiment",
            "Comments",
        ]
        display_cols = [c for c in display_cols if c in results.columns]

        display_df = results[display_cols].copy()

        if "Volume" in display_df.columns:
            display_df["Volume"] = display_df["Volume"].apply(format_volume)

        for col in ["LTP", "VWAP", "5EMA", "20EMA", "Target", "Stoploss"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(_safe_currency)

        if "ML Confidence" in display_df.columns:
            display_df["ML Confidence"] = display_df["ML Confidence"].apply(
                lambda x: f"{x*100:.0f}%" if isinstance(x, (int, float)) and not pd.isna(x) else "N/A"
            )

        styled_df = style_dataframe(display_df)
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=min(60 * len(display_df) + 40, 600),
        )

        st.markdown("---")
        st.markdown("### \U0001F4C8 Stock Chart")
        st.markdown(
            "<p style='color: #666; font-size: 0.8rem;'>Select a stock from the table above to view its chart</p>",
            unsafe_allow_html=True,
        )

        symbols_list = results["Symbol"].tolist()
        selected_chart_stock = st.selectbox("Choose a stock to chart", symbols_list, key="chart_selector")

        if selected_chart_stock:
            with st.spinner(f"Loading chart for {selected_chart_stock}..."):
                sym_row = results[results["Symbol"] == selected_chart_stock].iloc[0]
                sym_sector = sym_row.get("Sector", "")
                sym_index = sym_row.get("Index", "")
                sym_price_time = sym_row.get("Price Time", "")
                sym_market_cap = sym_row.get("Market Cap", "")
                index_badge = (
                    f"<span class='nifty50-badge'>{sym_index}</span>"
                    if sym_index == "NIFTY 50"
                    else f"<span class='broader-badge'>{sym_index}</span>"
                )
                st.markdown(
                    f"<p style='color: #888; font-size: 0.8rem;'>"
                    f"{sym_sector} &nbsp;&middot;&nbsp; {index_badge}"
                    f"&nbsp;&middot;&nbsp; {sym_market_cap}"
                    f"&nbsp;&middot;&nbsp; {sym_price_time}"
                    f"</p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='color: #888; font-size: 0.8rem;'>{sym_sector} &nbsp;&middot;&nbsp; {index_badge}</p>",
                    unsafe_allow_html=True,
                )

                chart_df = fetch_chart_data(selected_chart_stock)

                if chart_df is not None and not chart_df.empty:
                    fig = create_candlestick_chart(chart_df, selected_chart_stock)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Could not load chart data for {selected_chart_stock}")

        st.markdown("---")
        st.markdown("### \U0001F4E5 Export Data")

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_data = export_to_csv(results)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"scanner_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            xlsx_data = export_to_excel(results)
            st.download_button(
                label="Download Excel",
                data=xlsx_data,
                file_name=f"scanner_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

# ---------------------------------------------------------------------------
# Second tab: Sector Breakdown
# ---------------------------------------------------------------------------
with tab_sectors:
    st.markdown("### \U0001F3ED Sector Breakdown")
    st.markdown(
        "<p style='color: #666; font-size: 0.8rem;'>"
        "Nifty 50 constituents and broader market stocks categorized by sector. "
        "Hover or click for details.</p>",
        unsafe_allow_html=True,
    )

    sector_df = st.session_state.get("sector_dataframe", pd.DataFrame())

    if not sector_df.empty:
        col1, col2 = st.columns([1, 1])

        with col1:
            fig_sector = px.bar(
                sector_df, x="Sector", y="Total Stocks",
                color="Sector", title="Stocks per Sector",
                text="Total Stocks",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_sector.update_layout(
                template="plotly_dark", paper_bgcolor="#0E0F10", plot_bgcolor="#151618",
                showlegend=False, height=400, margin=dict(l=40, r=20, t=40, b=80),
                font=dict(color="#E0E0E0"), xaxis_tickangle=-45,
            )
            fig_sector.update_traces(textposition="outside")
            st.plotly_chart(fig_sector, use_container_width=True)

        with col2:
            sector_melted = sector_df.melt(
                id_vars=["Sector"],
                value_vars=["Nifty 50", "Broader Market"],
                var_name="Index Membership", value_name="Count",
            )
            fig_stacked = px.bar(
                sector_melted, x="Sector", y="Count",
                color="Index Membership",
                title="Nifty 50 vs Broader Market by Sector",
                barmode="stack", text="Count",
                color_discrete_map={"Nifty 50": "#FF6B35", "Broader Market": "#448AFF"},
            )
            fig_stacked.update_layout(
                template="plotly_dark", paper_bgcolor="#0E0F10", plot_bgcolor="#151618",
                height=400, margin=dict(l=40, r=20, t=40, b=80),
                font=dict(color="#E0E0E0"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_tickangle=-45,
            )
            fig_stacked.update_traces(textposition="inside")
            st.plotly_chart(fig_stacked, use_container_width=True)

        st.markdown("### \U0001F4CB Sector Details")
        st.dataframe(
            sector_df.style.map(
                lambda v: "color: #FF6B35; font-weight: bold;",
                subset=["Nifty 50"],
            ).set_table_styles([
                {"selector": "thead tr th", "props": "background-color: #1e1e1e; color: #ffffff; font-weight: 600; padding: 8px 12px;"},
                {"selector": "tbody tr:nth-child(even)", "props": "background-color: #1a1a1a;"},
                {"selector": "tbody tr:nth-child(odd)", "props": "background-color: #222222;"},
                {"selector": "td", "props": "padding: 6px 12px; color: #E0E0E0;"},
            ]),
            use_container_width=True,
        )

        st.markdown("### \U0001F3C6 Nifty 50 Sector Distribution")
        nifty50_sector_df = sector_df[sector_df["Nifty 50"] > 0][
            ["Sector", "Nifty 50"]
        ].sort_values("Nifty 50", ascending=False)

        if not nifty50_sector_df.empty:
            fig_pie = px.pie(
                nifty50_sector_df, names="Sector", values="Nifty 50",
                title="Nifty 50 Constituents by Sector",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_pie.update_layout(
                template="plotly_dark", paper_bgcolor="#0E0F10", plot_bgcolor="#151618",
                height=450, font=dict(color="#E0E0E0"),
            )
            fig_pie.update_traces(textposition="inside", textinfo="label+percent")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Run a scan first to see sector breakdown.")

# ---------------------------------------------------------------------------
# Third tab: Top 5 picks
# ---------------------------------------------------------------------------
with tab_toppicks:
    st.markdown("### \U0001F3C6 Top 5 Picks")
    st.markdown(
        "<p style='color: #666; font-size: 0.8rem;'>Highest-scoring stocks across all sectors</p>",
        unsafe_allow_html=True,
    )

    if not results.empty:
        top5 = get_top_picks(results, n=5)

        if not top5.empty:
            cols = st.columns(min(5, len(top5)))
            for i, (_, row) in enumerate(top5.iterrows()):
                with cols[i % len(cols)]:
                    score_color = "#00E676" if row["Score"] >= 8 else "#FFD54F"
                    action_emoji = "BUY" if row["Action"] == "BUY" else "WATCH" if row["Action"] == "WATCH" else "AVOID"
                    index_badge = (
                        "<span class='nifty50-badge'>NIFTY 50</span>"
                        if row.get("Index") == "NIFTY 50"
                        else "<span class='broader-badge'>Broader</span>"
                    )

                    st.markdown(
                        f"""
                        <div class="top-pick-card">
                            <div class="top-pick-symbol">{row['Symbol']}</div>
                            <div style="margin: 4px 0;">{index_badge}</div>
                            <div style="font-size: 0.75rem; color: #888; margin-bottom: 4px;">{row.get('Sector', '')}</div>
                            <div class="top-pick-score" style="color: {score_color};">{row['Score']}/10</div>
                            <div class="top-pick-detail">LTP: Rs{row['LTP']:,.2f}</div>
                            <div class="top-pick-detail">RSI: {row['RSI']}</div>
                            <div class="top-pick-detail">{action_emoji}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("### \U0001F4CA All Top Picks")
            top_display_cols = [
                "Symbol", "Company", "Sector", "Market Cap", "Index",
                "LTP", "RSI", "Score", "Action", "Target", "Stoploss"
            ]
            top_display_cols = [c for c in top_display_cols if c in top5.columns]
            tp_df = top5[top_display_cols].copy()

            for col in ["LTP", "Target", "Stoploss"]:
                if col in tp_df.columns:
                    tp_df[col] = tp_df[col].apply(_safe_currency)

            st.dataframe(
                style_dataframe(tp_df),
                use_container_width=True,
            )
        else:
            st.info("No top picks available. Run a scan first.")
    else:
        st.info("Run a scan to see top picks.")
