"""
app.py — AI Intraday Trading Scanner (Streamlit Dashboard)
============================================================
Professional intraday stock scanner dashboard for NSE equities.

Architecture:
  - Frontend: Streamlit with custom dark theme (Bloomberg-style)
  - Backend: Graph-pipeline scanner (inspired by ScrapeGraphAI)
  - Data: yfinance for 5-minute intraday data
  - Charts: Plotly candlestick with VWAP + EMA overlays

Features:
  - Live auto-refresh (60s) with toggle
  - Sector filter + score/RSI thresholds
  - Color-coded results table with target/SL
  - Interactive Plotly charts for selected stock
  - Top 5 picks section
  - CSV/Excel export
"""

import datetime
import logging

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Bloomberg Terminal Dark Theme
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* Main background */
    .stApp {
        background-color: #0E0F10;
        color: #E0E0E0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1A1A1D;
        border-right: 1px solid #2A2A2D;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #CCCCCC;
    }

    /* Headers */
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }

    /* Metric cards */
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

    /* Buttons */
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

    /* Select boxes */
    .stSelectbox > div > div {
        background-color: #1A1A1D;
        border-color: #2A2A2D;
        color: #E0E0E0;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        background-color: transparent;
    }
    [data-testid="stDataFrame"] table {
        font-size: 13px;
    }

    /* Tabs */
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

    /* Divider */
    hr {
        border-color: #2A2A2D !important;
        margin: 8px 0 !important;
    }

    /* Status badge */
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

    /* Download buttons */
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

    /* Checkbox */
    .stCheckbox > label {
        color: #CCCCCC !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-color: #2962FF !important;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        background-color: #1A1A1D !important;
        border: 1px solid #2A2A2D !important;
        color: #E0E0E0 !important;
    }

    /* Ensure plotly charts fit */
    .js-plotly-plot, .plot-container {
        width: 100% !important;
    }

    /* Top picks cards */
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
from scanner import scan_stocks, calculate_target_sl
from indicators import (
    calculate_vwap,
    calculate_ema,
)
from stocks_db import get_sectors, get_symbol_count
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
# Helper Functions (must be defined before usage)
# ---------------------------------------------------------------------------
def create_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """
    Create a professional candlestick chart with VWAP, EMA5, EMA20, and volume.
    """
    vwap = calculate_vwap(df)
    ema5 = calculate_ema(df, period=5)
    ema20 = calculate_ema(df, period=20)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00C853",
            decreasing_line_color="#FF5252",
            line=dict(width=1),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=vwap,
            name="VWAP",
            line=dict(color="#FF6D00", width=1.5, dash="dash"),
            opacity=0.8,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=ema5,
            name="5 EMA",
            line=dict(color="#448AFF", width=1.5),
            opacity=0.9,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=ema20,
            name="20 EMA",
            line=dict(color="#FFAB40", width=1.5),
            opacity=0.9,
        ),
        row=1,
        col=1,
    )

    colors = np.where(df["Close"].values >= df["Open"].values, "#00C853", "#FF5252")
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.6,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=dict(
            text=f"{symbol} — Intraday (5min)",
            font=dict(size=16, color="#FFFFFF"),
            x=0.02,
        ),
        template="plotly_dark",
        paper_bgcolor="#0E0F10",
        plot_bgcolor="#151618",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(l=40, r=20, t=50, b=30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
        ),
    )

    fig.update_yaxes(title_text="Price (₹)", row=1, col=1, gridcolor="#2A2A2D")
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor="#2A2A2D")
    fig.update_xaxes(gridcolor="#2A2A2D", row=1, col=1)
    fig.update_xaxes(gridcolor="#2A2A2D", row=2, col=1)

    return fig


def _safe_currency(val) -> str:
    """Format value as currency, handling NaN and non-numeric types."""
    try:
        if pd.isna(val):
            return "N/A"
        return f"₹{val:,.2f}"
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

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
if st.session_state.auto_refresh and _HAS_AUTOREFRESH:
    _ = st_autorefresh(interval=AUTO_REFRESH_INTERVAL_MS, key="auto_refresh")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
col_logo, col_title, col_status, col_time, col_refresh = st.columns([0.5, 3, 2, 2, 1.5])

with col_logo:
    st.markdown("### 📊")

with col_title:
    st.markdown(
        "<h1 style='margin: 0; font-size: 1.5rem;'>AI Intraday Trading Scanner</h1>"
        "<p style='margin: 0; color: #666; font-size: 0.75rem;'>NSE Equity Scanner · yfinance · 5min Data</p>",
        unsafe_allow_html=True,
    )

with col_status:
    market_open = is_market_open()
    status_class = "status-open" if market_open else "status-closed"
    status_text = "● LIVE" if market_open else "● CLOSED"
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%;'>"
        f"<span class='status-badge {status_class}'>{status_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

with col_time:
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%; color: #888; font-size: 0.85rem;'>"
        f"🕐 {get_ist_time()} IST"
        f"</div>",
        unsafe_allow_html=True,
    )

with col_refresh:
    refresh_status = "ON" if st.session_state.auto_refresh else "OFF"
    refresh_secs = AUTO_REFRESH_INTERVAL_MS // 1000
    st.markdown(
        f"<div style='display: flex; align-items: center; height: 100%; color: #888; font-size: 0.75rem;'>"
        f"🔄 Auto: {refresh_status} ({refresh_secs}s)"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin: 8px 0 16px 0;'>", unsafe_allow_html=True)

# Show market closed banner
if not market_open:
    st.warning(
        "🚫 **Market is currently closed.** NSE trading hours: Mon-Fri, 9:15 AM - 3:30 PM IST. "
        "Data shown is from the last trading session."
    )

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    st.markdown("---")

    # Sector selector
    sectors = get_sectors()
    selected_sector = st.selectbox(
        "Sector",
        sectors,
        index=sectors.index(st.session_state.sector) if st.session_state.sector in sectors else 0,
        key="sector_select",
    )

    # Score filter
    min_score = st.slider(
        "Minimum Score",
        min_value=0,
        max_value=10,
        value=st.session_state.min_score,
        step=1,
        help="Filter stocks by minimum score (0-10). 8+ = BUY, 6-7 = WATCH",
    )

    # RSI filter
    min_rsi = st.slider(
        "Minimum RSI",
        min_value=0,
        max_value=100,
        value=st.session_state.min_rsi,
        step=5,
        help="Filter stocks by minimum RSI value",
    )

    st.markdown("---")

    # Auto refresh toggle
    auto_refresh = st.checkbox(
        "Auto Refresh (every 60s)",
        value=st.session_state.auto_refresh,
        help="Automatically refresh data every 60 seconds",
    )

    # Manual scan button
    scan_clicked = st.button(
        "🔍 Scan Now",
        type="primary",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### 📈 Legend")
    st.markdown(
        """
        <div style="font-size: 0.8rem; color: #888;">
            <p><span style="color: #00E676; font-weight: bold;">🟢 BUY</span> — Score 8-10</p>
            <p><span style="color: #FFD54F; font-weight: bold;">🟡 WATCH</span> — Score 6-7</p>
            <p><span style="color: #EF5350; font-weight: bold;">🔴 AVOID</span> — Score 0-5</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 0.7rem; color: #555; text-align: center;'>"
        "Data Source: yfinance<br>"
        "Built for educational purposes<br>"
        "v2.0.0"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Update session state
# ---------------------------------------------------------------------------
st.session_state.auto_refresh = auto_refresh
st.session_state.sector = selected_sector
st.session_state.min_score = min_score
st.session_state.min_rsi = min_rsi

# ---------------------------------------------------------------------------
# Main Panel — Two Tabs
# ---------------------------------------------------------------------------
tab_scanner, tab_toppicks = st.tabs(["📋 Scanner Results", "🏆 Top 5 Picks"])

with tab_scanner:
    # Run scan when button is clicked or on first load
    if scan_clicked or st.session_state.scan_results.empty:
        with st.spinner(f"🔍 Scanning {selected_sector} sector..."):
            try:
                results = scan_stocks(
                    sector=selected_sector,
                    min_score=min_score,
                    min_rsi=min_rsi,
                )
                st.session_state.scan_results = results
                st.session_state.last_scan_time = datetime.datetime.now()
            except Exception as e:
                st.error(f"Scan failed: {str(e)}")
                st.session_state.scan_results = pd.DataFrame()

    results = st.session_state.scan_results

    # Display results count and last scan time
    if not results.empty:
        last_time = st.session_state.last_scan_time
        time_str = last_time.strftime("%I:%M:%S %p") if last_time else "N/A"

        total_stocks = get_symbol_count(selected_sector)
        scanned_count = len(results)
        buy_count = len(results[results["Action"] == "BUY"])
        watch_count = len(results[results["Action"] == "WATCH"])
        avoid_count = scanned_count - buy_count - watch_count

        col_info, col_buy, col_watch, col_avoid = st.columns(4)
        with col_info:
            st.metric("Stocks Scanned", str(total_stocks), f"{scanned_count} passed filters")
        with col_buy:
            st.metric("🟢 BUY Signals", buy_count)
        with col_watch:
            st.metric("🟡 WATCH Signals", watch_count)
        with col_avoid:
            st.metric("🔴 Avoid/Filtered", max(avoid_count, 0))
        st.markdown(f"<p style='color: #666; font-size: 0.8rem;'>Last scan: {time_str} IST</p>", unsafe_allow_html=True)
    else:
        st.info("No stocks match your criteria. Try lowering the score/RSI filters or select a different sector.")

    # Results table
    if not results.empty:
        st.markdown("### 📊 Scanner Results")

        # Prepare display columns
        display_cols = [
            "Symbol", "LTP", "VWAP", "5EMA", "20EMA",
            "RSI", "Volume", "Score", "Action",
            "Target", "Stoploss",
            "ML Confidence", "Pattern", "Sentiment",
            "Comments",
        ]
        display_cols = [c for c in display_cols if c in results.columns]

        display_df = results[display_cols].copy()

        # Format volume
        if "Volume" in display_df.columns:
            display_df["Volume"] = display_df["Volume"].apply(format_volume)

        # Format currency columns
        for col in ["LTP", "VWAP", "5EMA", "20EMA", "Target", "Stoploss"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(_safe_currency)

        # Format ML columns
        if "ML Confidence" in display_df.columns:
            display_df["ML Confidence"] = display_df["ML Confidence"].apply(
                lambda x: f"{x*100:.0f}%" if isinstance(x, (int, float)) and not pd.isna(x) else "N/A"
            )

        # Style and display
        styled_df = style_dataframe(display_df)
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=min(60 * len(display_df) + 40, 600),
        )

        # Stock chart section
        st.markdown("---")
        st.markdown("### 📈 Stock Chart")
        st.markdown(
            "<p style='color: #666; font-size: 0.8rem;'>Select a stock from the table above to view its chart</p>",
            unsafe_allow_html=True,
        )

        # Stock selector for chart
        symbols_list = results["Symbol"].tolist()
        selected_chart_stock = st.selectbox(
            "Choose a stock to chart",
            symbols_list,
            key="chart_selector",
        )

        if selected_chart_stock:
            with st.spinner(f"Loading chart for {selected_chart_stock}..."):
                chart_df = fetch_chart_data(selected_chart_stock)

                if chart_df is not None and not chart_df.empty:
                    fig = create_candlestick_chart(chart_df, selected_chart_stock)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Could not load chart data for {selected_chart_stock}")

        # Export section
        st.markdown("---")
        st.markdown("### 📥 Export Data")

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_data = export_to_csv(results)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"scanner_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            xlsx_data = export_to_excel(results)
            st.download_button(
                label="📗 Download Excel",
                data=xlsx_data,
                file_name=f"scanner_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

# Second tab: Top 5 picks
with tab_toppicks:
    st.markdown("### 🏆 Top 5 Picks")
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
                    action_emoji = "🟢" if row["Action"] == "BUY" else "🟡" if row["Action"] == "WATCH" else "🔴"

                    st.markdown(
                        f"""
                        <div class="top-pick-card">
                            <div class="top-pick-symbol">{row['Symbol']}</div>
                            <div class="top-pick-score" style="color: {score_color};">{row['Score']}/10</div>
                            <div class="top-pick-detail">LTP: ₹{row['LTP']:,.2f}</div>
                            <div class="top-pick-detail">RSI: {row['RSI']}</div>
                            <div class="top-pick-detail">{action_emoji} {row['Action']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("### 📊 All Top Picks")
            top_display_cols = ["Symbol", "LTP", "RSI", "Score", "Action", "Target", "Stoploss"]
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

