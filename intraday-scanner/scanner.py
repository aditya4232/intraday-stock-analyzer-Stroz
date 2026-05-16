"""
scanner.py — Graph-Pipeline Scanning Engine
============================================
Inspired by ScrapeGraphAI's node-based pipeline architecture.

Pipeline:
  [FetchNode] -> [IndicatorNode] -> [EvaluateNode] -> [ScoreNode] -> [RenderNode]

Each node in the pipeline is a self-contained step. The pipeline is orchestrated
by scan_stocks() which handles:
  - Progress tracking
  - Error handling per stock
  - Rate limiting between API calls
  - Filtering by score/RSI thresholds
  - DataFrame assembly with targets and stoplosses
"""

import logging
import time as _time
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd
import streamlit as st

from indicators import (
    calculate_vwap,
    calculate_ema,
    calculate_rsi,
    evaluate_all_conditions,
    compute_score,
    classify_action,
    get_comment,
)
from stocks_db import get_symbols
from ml_model import analyze_stock
from config import (
    SCAN_RETRY_COUNT,
    SCAN_RATE_LIMIT_SECONDS,
    SCAN_TIMEOUT_SECONDS,
    TARGET_PCT,
    STOPLOSS_PCT,
)

logger = logging.getLogger(__name__)

# Sentinel value to prevent StreamlitDuplicateElement errors across reruns
_SCAN_IN_PROGRESS = False


# ---------------------------------------------------------------------------
# Pipeline Node: FetchNode
# ---------------------------------------------------------------------------
def _fetch_node(symbol: str, progress_callback: Optional[Callable] = None) -> Optional[pd.DataFrame]:
    """
    FetchNode: Download 5-minute intraday data from yfinance.
    Returns a clean DataFrame or None on failure.
    """
    import yfinance as yf

    max_retries = SCAN_RETRY_COUNT
    for attempt in range(1, max_retries + 1):
        try:
            if progress_callback:
                progress_callback(symbol, "fetching")

            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval="5m")

            if df is None or df.empty:
                if attempt < max_retries:
                    _time.sleep(1)
                    continue
                return None

            # Flatten MultiIndex columns (yfinance bug workaround)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [" ".join(col).strip() for col in df.columns]
                # Rename to standard names
                rename_map = {}
                for col in df.columns:
                    col_lower = col.lower()
                    if "open" in col_lower:
                        rename_map[col] = "Open"
                    elif "high" in col_lower:
                        rename_map[col] = "High"
                    elif "low" in col_lower:
                        rename_map[col] = "Low"
                    elif "close" in col_lower:
                        rename_map[col] = "Close"
                    elif "volume" in col_lower:
                        rename_map[col] = "Volume"
                df = df.rename(columns=rename_map)

            # Validate required columns exist
            required = ["Open", "High", "Low", "Close", "Volume"]
            if not all(c in df.columns for c in required):
                if attempt < max_retries:
                    _time.sleep(1)
                    continue
                return None

            # Ensure we have enough data for indicators
            if len(df) < 25:
                return None

            return df

        except Exception as e:
            logger.warning("FetchNode failed for %s (attempt %d): %s", symbol, attempt, e)
            if attempt < max_retries:
                _time.sleep(1)
                continue
            return None

    return None


# ---------------------------------------------------------------------------
# Pipeline Node: IndicatorNode
# ---------------------------------------------------------------------------
def _indicator_node(df: pd.DataFrame) -> dict | None:
    """
    IndicatorNode: Calculate all technical indicators and evaluate conditions.
    Returns a dict with computed values and condition flags.
    """
    try:
        vwap_series = calculate_vwap(df)
        ema5_series = calculate_ema(df, period=5)
        ema20_series = calculate_ema(df, period=20)
        rsi_series = calculate_rsi(df["Close"])

        conditions = evaluate_all_conditions(df)
        score = compute_score(conditions)
        action = classify_action(score)
        comment = get_comment(score, conditions)

        ltp = float(df["Close"].iloc[-1])
        vwap_val = float(vwap_series.iloc[-1]) if not pd.isna(vwap_series.iloc[-1]) else 0.0
        ema5_val = float(ema5_series.iloc[-1]) if not pd.isna(ema5_series.iloc[-1]) else 0.0
        ema20_val = float(ema20_series.iloc[-1]) if not pd.isna(ema20_series.iloc[-1]) else 0.0
        rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 0.0
        volume_val = int(df["Volume"].iloc[-1]) if not pd.isna(df["Volume"].iloc[-1]) else 0

        target, stoploss = calculate_target_sl(ltp)

        # ML analysis (confidence, anomaly, pattern, sentiment)
        ml_result = analyze_stock(df, conditions)

        return {
            "Symbol": df.attrs.get("symbol", ""),
            "LTP": round(ltp, 2),
            "VWAP": round(vwap_val, 2),
            "5EMA": round(ema5_val, 2),
            "20EMA": round(ema20_val, 2),
            "RSI": round(rsi_val, 1),
            "Volume": volume_val,
            "Score": score,
            "Action": action,
            "Target": round(target, 2),
            "Stoploss": round(stoploss, 2),
            "Comments": comment,
            # Condition flags (for debugging/filtering)
            "▴ VWAP": conditions.get("vwap", False),
            "▴ EMA": conditions.get("ema", False),
            "▴ RSI": conditions.get("rsi", False),
            "▴ Vol": conditions.get("volume", False),
            "▴ Brk": conditions.get("candle_breakout", False),
            "Green": conditions.get("green_candle", False),
            # ML fields
            "ML Confidence": ml_result["ml_confidence"],
            "Anomaly": ml_result["anomaly_score"],
            "Pattern": ml_result["pattern"],
            "Sentiment": ml_result["sentiment"],
        }
    except Exception as e:
        logger.warning("IndicatorNode failed for %s: %s", df.attrs.get("symbol", "unknown"), e)
        return None


def calculate_target_sl(ltp: float) -> tuple[float, float]:
    """
    Calculate intraday target and stoploss prices.

    Target: LTP × TARGET_PCT (default +1.5%)
    Stoploss: LTP × STOPLOSS_PCT (default -0.5%)
    """
    target = ltp * TARGET_PCT
    stoploss = ltp * STOPLOSS_PCT
    return target, stoploss


# ---------------------------------------------------------------------------
# Pipeline Orchestrator
# ---------------------------------------------------------------------------
def scan_stocks(
    sector: str,
    min_score: int = 0,
    min_rsi: float = 0.0,
) -> pd.DataFrame:
    """
    Orchestrate the full scanning pipeline.

    Parameters
    ----------
    sector : str
        Sector name from stocks_db.get_sectors()
    min_score : int
        Minimum score filter (0-10)
    min_rsi : float
        Minimum RSI filter

    Returns
    -------
    pd.DataFrame
        Results sorted by Score descending
    """
    global _SCAN_IN_PROGRESS
    if _SCAN_IN_PROGRESS:
        logger.warning("Scan already in progress, skipping duplicate request")
        return st.session_state.get("scan_results", pd.DataFrame())

    symbols = get_symbols(sector)
    if not symbols:
        return pd.DataFrame()

    _SCAN_IN_PROGRESS = True
    results: list[dict] = []
    total = len(symbols)
    deadline = datetime.now() + timedelta(seconds=SCAN_TIMEOUT_SECONDS)

    # Progress tracking — use st.status for Streamlit >=1.28 compatibility
    status_placeholder = st.empty()
    with status_placeholder.container():
        progress_bar = st.progress(0, text="Initializing scan...")
        progress_text = st.markdown(
            f"<small style='color: #888;'>Scanning {sector} ({total} stocks)...</small>",
            unsafe_allow_html=True,
        )

        for idx, symbol in enumerate(symbols):
            # Enforce time budget for free-tier timeout safety
            if datetime.now() >= deadline:
                logger.warning("Scan timeout reached after %d/%d stocks", idx, total)
                break

            try:
                pct = (idx + 1) / total
                progress_bar.progress(pct)
                progress_text.markdown(
                    f"<small style='color: #888;'>[{idx + 1}/{total}] {symbol.replace('.NS', '')}...</small>",
                    unsafe_allow_html=True,
                )

                raw_symbol = symbol.replace(".NS", "")
                df = _fetch_node(symbol)

                if df is None:
                    continue

                df.attrs["symbol"] = raw_symbol

                result = _indicator_node(df)
                if result is None:
                    continue

                if result["Score"] < min_score:
                    continue
                if min_rsi > 0 and result["RSI"] < min_rsi:
                    continue

                results.append(result)

            except Exception as e:
                logger.warning("Pipeline error for %s: %s", symbol, e)
                continue
            finally:
                _time.sleep(SCAN_RATE_LIMIT_SECONDS)

    status_placeholder.empty()
    _SCAN_IN_PROGRESS = False

    if not results:
        return pd.DataFrame()

    df_results = pd.DataFrame(results)

    # Sort by score descending, then RSI descending
    df_results = df_results.sort_values(
        by=["Score", "RSI"], ascending=[False, False]
    ).reset_index(drop=True)

    return df_results


def scan_stocks_silent(
    sector: str,
    min_score: int = 0,
    min_rsi: float = 0.0,
) -> pd.DataFrame:
    """
    Silent version of scan_stocks without Streamlit progress UI.
    Used for background/scheduled scans.
    """
    symbols = get_symbols(sector)
    if not symbols:
        return pd.DataFrame()

    results: list[dict] = []

    for symbol in symbols:
        try:
            raw_symbol = symbol.replace(".NS", "")
            df = _fetch_node(symbol)
            if df is None:
                continue

            df.attrs["symbol"] = raw_symbol
            result = _indicator_node(df)
            if result is None:
                continue

            if result["Score"] < min_score:
                continue
            if min_rsi > 0 and result["RSI"] < min_rsi:
                continue

            results.append(result)
        except Exception as e:
            logger.warning("Silent scan error for %s: %s", symbol, e)
            continue
        finally:
            _time.sleep(SCAN_RATE_LIMIT_SECONDS)

    if not results:
        return pd.DataFrame()

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(
        by=["Score", "RSI"], ascending=[False, False]
    ).reset_index(drop=True)

    return df_results


if __name__ == "__main__":
    # Quick self-test
    print("Testing scanner pipeline...")
    df = scan_stocks_silent("Banking", min_score=0)
    if not df.empty:
        print(f"Found {len(df)} stocks meeting criteria")
        print(df[["Symbol", "LTP", "RSI", "Score", "Action"]].head(10).to_string())
    else:
        print("No stocks found (market may be closed)")
