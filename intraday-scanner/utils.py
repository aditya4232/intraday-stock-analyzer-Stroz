"""
utils.py — Utility Functions
=============================
Helper functions for:
  - Market hours checking (Indian NSE: Mon-Fri, 9:15-15:30 IST)
  - Data export (CSV, Excel)
  - Dataframe styling (color-coded actions)
  - Fetching chart data for a single stock
  - Formatting numbers for display
"""

import io
import logging
import time as _time
from datetime import datetime, time, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import (
    MARKET_OPEN_HOUR, MARKET_OPEN_MIN,
    MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN,
    IST_OFFSET_HOURS, IST_OFFSET_MINUTES,
    SCAN_RETRY_COUNT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Indian Market Hours
# ---------------------------------------------------------------------------
def is_market_open() -> bool:
    """
    Check if the Indian stock market is currently open.

    NSE Trading Hours:
      - Monday to Friday
      - 9:15 AM to 3:30 PM IST (UTC+5:30)

    Returns
    -------
    bool
        True if market is open
    """
    # Get current time in IST
    ist = timezone(timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES))
    now_ist = datetime.now(ist)

    if now_ist.weekday() >= 5:
        return False

    market_open = time(MARKET_OPEN_HOUR, MARKET_OPEN_MIN)
    market_close = time(MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN)
    current_time = now_ist.time()

    return market_open <= current_time <= market_close


def get_ist_time() -> str:
    """
    Get current Indian Standard Time as a formatted string.

    Returns
    -------
    str
        Formatted time string like "11:45:30 AM"
    """
    ist = timezone(timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES))
    now_ist = datetime.now(ist)
    return now_ist.strftime("%I:%M:%S %p")


# ---------------------------------------------------------------------------
# Chart Data Fetching
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def fetch_chart_data(symbol: str) -> Optional[pd.DataFrame]:
    """
    Fetch intraday chart data for a single stock.
    Used for the Plotly candlestick chart.

    Parameters
    ----------
    symbol : str
        NSE symbol (e.g., 'HDFCBANK') — .NS is appended automatically

    Returns
    -------
    pd.DataFrame or None
        DataFrame with OHLCV data, or None on failure
    """
    max_retries = SCAN_RETRY_COUNT
    for attempt in range(1, max_retries + 1):
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(period="2d", interval="5m", timeout=10)

            if df is None or df.empty:
                if attempt < max_retries:
                    _time.sleep(1)
                continue

            # Flatten MultiIndex if needed
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [" ".join(col).strip() for col in df.columns]
                rename_map = {}
                for col in df.columns:
                    cl = col.lower()
                    if "open" in cl:
                        rename_map[col] = "Open"
                    elif "high" in cl:
                        rename_map[col] = "High"
                    elif "low" in cl:
                        rename_map[col] = "Low"
                    elif "close" in cl:
                        rename_map[col] = "Close"
                    elif "volume" in cl:
                        rename_map[col] = "Volume"
                df = df.rename(columns=rename_map)

            return df

        except Exception as e:
            logger.warning("Chart data fetch failed for %s (attempt %d): %s", symbol, attempt, e)
            if attempt < max_retries:
                _time.sleep(1)
            continue

    logger.error("Chart data fetch failed for %s after %d attempts", symbol, max_retries)
    return None


# ---------------------------------------------------------------------------
# Data Export
# ---------------------------------------------------------------------------
def export_to_csv(df: pd.DataFrame) -> bytes:
    """
    Export DataFrame to CSV bytes.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe

    Returns
    -------
    bytes
        CSV file content as bytes
    """
    output = io.BytesIO()
    df_to_export = df.copy()
    # Remove helper condition columns
    helper_cols = ["▴ VWAP", "▴ EMA", "▴ RSI", "▴ Vol", "▴ Brk", "Green"]
    df_to_export = df_to_export.drop(
        columns=[c for c in helper_cols if c in df_to_export.columns],
        errors="ignore",
    )
    df_to_export.to_csv(output, index=False)
    output.seek(0)
    return output.getvalue()


def export_to_excel(df: pd.DataFrame) -> bytes:
    """
    Export DataFrame to Excel bytes.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe

    Returns
    -------
    bytes
        Excel file content as bytes
    """
    output = io.BytesIO()
    df_to_export = df.copy()
    helper_cols = ["▴ VWAP", "▴ EMA", "▴ RSI", "▴ Vol", "▴ Brk", "Green"]
    df_to_export = df_to_export.drop(
        columns=[c for c in helper_cols if c in df_to_export.columns],
        errors="ignore",
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_export.to_excel(writer, sheet_name="Scanner Results", index=False)
    output.seek(0)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Dataframe Styling
# ---------------------------------------------------------------------------
def style_dataframe(df: pd.DataFrame):
    """
    Apply professional color styling to the results dataframe.

    - BUY rows: green background
    - WATCH rows: amber/yellow background
    - AVOID rows: light red background

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe with an 'Action' column

    Returns
    -------
    pd.io.formats.style.Styler
        Styled dataframe
    """
    if df.empty:
        return df.style

    def _color_action(val: str) -> str:
        if val == "BUY":
            return "background-color: #1b5e20; color: #ffffff; font-weight: bold;"
        elif val == "WATCH":
            return "background-color: #f57f17; color: #ffffff; font-weight: bold;"
        elif val == "AVOID":
            return "background-color: #b71c1c; color: #ffffff; font-weight: bold;"
        return ""

    def _color_score(val) -> str:
        try:
            v = int(val)
            if v >= 8:
                return "color: #00e676; font-weight: bold;"
            elif v >= 6:
                return "color: #ffd54f; font-weight: bold;"
            else:
                return "color: #ef5350;"
        except (ValueError, TypeError):
            return ""

    def _color_rsi(val) -> str:
        try:
            v = float(val)
            if v >= 70:
                return "color: #00e676;"
            elif v >= 60:
                return "color: #69f0ae;"
            elif v >= 50:
                return "color: #ffd54f;"
            else:
                return "color: #ef5350;"
        except (ValueError, TypeError):
            return ""

    # Define columns to style
    styled = df.style

    if "Action" in df.columns:
        styled = styled.map(_color_action, subset=["Action"])

    if "Score" in df.columns:
        styled = styled.map(_color_score, subset=["Score"])

    if "RSI" in df.columns:
        styled = styled.map(_color_rsi, subset=["RSI"])

    # Zebra striping for readability
    styled = styled.set_table_styles(
        [
            {"selector": "thead tr th", "props": "background-color: #1e1e1e; color: #ffffff; font-weight: 600; padding: 8px 12px; border-bottom: 2px solid #333;"},
            {"selector": "tbody tr:nth-child(even)", "props": "background-color: #1a1a1a;"},
            {"selector": "tbody tr:nth-child(odd)", "props": "background-color: #222222;"},
            {"selector": "tbody tr:hover", "props": "background-color: #2a2a2a;"},
            {"selector": "td", "props": "padding: 6px 12px; border-bottom: 1px solid #333;"},
            {"selector": "", "props": "border-collapse: collapse; font-size: 13px;"},
        ]
    )

    return styled


# ---------------------------------------------------------------------------
# Number Formatting
# ---------------------------------------------------------------------------
def format_volume(val: int) -> str:
    """Format volume in human-readable format (K, M, B)."""
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f}B"
    elif val >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    elif val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)


def format_currency(val: float) -> str:
    """Format currency with 2 decimal places."""
    return f"₹{val:,.2f}"


# ---------------------------------------------------------------------------
# Top Picks Calculation
# ---------------------------------------------------------------------------
def get_top_picks(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Extract top N picks sorted by Score then RSI.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe
    n : int
        Number of top picks

    Returns
    -------
    pd.DataFrame
        Top N rows
    """
    if df.empty:
        return df
    return df.head(n)


if __name__ == "__main__":
    print(f"Market open: {is_market_open()}")
    print(f"IST time: {get_ist_time()}")
