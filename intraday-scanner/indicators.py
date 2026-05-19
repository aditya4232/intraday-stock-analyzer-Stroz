"""
indicators.py — Technical Indicator Engine
===========================================
Implements all technical indicators used by the scanner.
Each indicator function is a self-contained, testable "node".

Indicators:
  - VWAP (Volume Weighted Average Price)
  - EMA (Exponential Moving Average) — 5 and 20 periods
  - RSI (Relative Strength Index) — Wilder's smoothing, 14 periods
  - Average Volume — rolling 20-period mean
  - Condition evaluation — 6 boolean checks for scoring
"""

import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd

from config import RSI_PERIOD, RSI_MOMENTUM_THRESHOLD, VOLUME_BREAKOUT_MULTIPLIER, BUY_THRESHOLD, WATCH_THRESHOLD

warnings.filterwarnings("ignore", category=RuntimeWarning)

logger = logging.getLogger(__name__)


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price with daily reset.

    VWAP = Σ(Volume × Typical Price) / Σ(Volume)
    Typical Price = (High + Low + Close) / 3

    Resets cumulative sum at the start of each trading day
    to produce correct intraday VWAP values.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: 'High', 'Low', 'Close', 'Volume'
        Index should be DatetimeIndex for daily reset.

    Returns
    -------
    pd.Series
        VWAP values for each row (cumulative within each day)
    """
    try:
        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
        volume = df["Volume"]
        pv = typical_price * volume

        if isinstance(df.index, pd.DatetimeIndex):
            dates = df.index.date
            cum_pv = pv.groupby(dates).cumsum()
            cum_vol = volume.groupby(dates).cumsum()
        else:
            cum_pv = pv.cumsum()
            cum_vol = volume.cumsum()

        cum_vol_safe = cum_vol.replace(0, np.nan)
        vwap = cum_pv / cum_vol_safe
        vwap = vwap.ffill()
        return vwap
    except (KeyError, Exception) as e:
        logger.warning("VWAP calculation failed: %s", e)
        return pd.Series(index=df.index, dtype=float)


def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Uses pandas ewm with span for accurate EMA computation.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'Close' column
    period : int
        EMA period (default 20)

    Returns
    -------
    pd.Series
        EMA values
    """
    try:
        return df["Close"].ewm(span=period, adjust=False).mean()
    except (KeyError, Exception) as e:
        logger.warning("EMA calculation failed: %s", e)
        return pd.Series(index=df.index, dtype=float)


def calculate_rsi(series: pd.Series, period: int = None) -> pd.Series:
    """
    Calculate Relative Strength Index using Wilder's smoothing method.

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss

    Parameters
    ----------
    series : pd.Series
        Price series (typically Close)
    period : int
        RSI period (default 14)

    Returns
    -------
    pd.Series
        RSI values (0-100), NaN for initial periods
    """
    if period is None:
        period = RSI_PERIOD
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))

        avg_gain = gain.rolling(window=period, min_periods=period).mean().copy()
        avg_loss = loss.rolling(window=period, min_periods=period).mean().copy()

        for i in range(period, len(avg_gain)):
            if pd.isna(avg_gain.iloc[i - 1]):
                continue
            avg_gain.iat[i] = (avg_gain.iat[i - 1] * (period - 1) + gain.iat[i]) / period
            avg_loss.iat[i] = (avg_loss.iat[i - 1] * (period - 1) + loss.iat[i]) / period

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.warning("RSI calculation failed: %s", e)
        return pd.Series(index=series.index, dtype=float)


def calculate_avg_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate rolling average volume.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'Volume' column
    period : int
        Rolling window period (default 20)

    Returns
    -------
    pd.Series
        Average volume values
    """
    try:
        return df["Volume"].rolling(window=period, min_periods=1).mean()
    except (KeyError, Exception) as e:
        logger.warning("Avg volume calculation failed: %s", e)
        return pd.Series(index=df.index, dtype=float)


def evaluate_vwap_condition(df: pd.DataFrame) -> bool:
    """
    Condition A: Current price > VWAP.
    Returns True if latest close is above VWAP.
    """
    try:
        vwap = calculate_vwap(df)
        if pd.isna(vwap.iloc[-1]):
            return False
        return bool(df["Close"].iloc[-1] > vwap.iloc[-1])
    except Exception as e:
        logger.debug("VWAP condition check failed: %s", e)
        return False


def evaluate_ema_condition(df: pd.DataFrame) -> bool:
    """
    Condition B: 5 EMA > 20 EMA (bullish alignment).
    Returns True if fast EMA is above slow EMA.
    """
    try:
        ema5 = calculate_ema(df, period=5)
        ema20 = calculate_ema(df, period=20)
        if pd.isna(ema5.iloc[-1]) or pd.isna(ema20.iloc[-1]):
            return False
        return bool(ema5.iloc[-1] > ema20.iloc[-1])
    except Exception as e:
        logger.debug("EMA condition check failed: %s", e)
        return False


def evaluate_rsi_condition(df: pd.DataFrame) -> bool:
    """
    Condition C: RSI > 60 (strong momentum).
    Returns True if RSI is above threshold.
    """
    try:
        rsi = calculate_rsi(df["Close"])
        if pd.isna(rsi.iloc[-1]):
            return False
        return bool(rsi.iloc[-1] > RSI_MOMENTUM_THRESHOLD)
    except Exception as e:
        logger.debug("RSI condition check failed: %s", e)
        return False


def evaluate_volume_breakout(df: pd.DataFrame) -> bool:
    """
    Condition D: Current candle volume > 1.5 * average volume.
    Returns True if volume is significantly above average.
    """
    try:
        current_volume = df["Volume"].iloc[-1]
        avg_volume = calculate_avg_volume(df).iloc[-1]
        if pd.isna(avg_volume) or avg_volume == 0 or pd.isna(current_volume):
            return False
        return bool(current_volume > VOLUME_BREAKOUT_MULTIPLIER * avg_volume)
    except Exception as e:
        logger.debug("Volume breakout check failed: %s", e)
        return False


def evaluate_candle_breakout(df: pd.DataFrame) -> bool:
    """
    Condition E: Current candle high > previous candle high.
    Returns True if new high is being made.
    """
    try:
        if len(df) < 2:
            return False
        return bool(df["High"].iloc[-1] > df["High"].iloc[-2])
    except Exception as e:
        logger.debug("Candle breakout check failed: %s", e)
        return False


def evaluate_green_candle(df: pd.DataFrame) -> bool:
    """
    Condition F (prerequisite): Close > Open (green candle).
    Returns True if current candle is bullish.
    """
    try:
        return bool(df["Close"].iloc[-1] > df["Open"].iloc[-1])
    except Exception as e:
        logger.debug("Green candle check failed: %s", e)
        return False


def evaluate_all_conditions(df: pd.DataFrame) -> dict[str, bool]:
    """
    Evaluate all 6 intraday conditions.

    Returns a dictionary of condition name to boolean result.
    Ordered by evaluation complexity (cheapest first for early exit).
    """
    return {
        "green_candle": evaluate_green_candle(df),
        "vwap": evaluate_vwap_condition(df),
        "ema": evaluate_ema_condition(df),
        "rsi": evaluate_rsi_condition(df),
        "volume": evaluate_volume_breakout(df),
        "candle_breakout": evaluate_candle_breakout(df),
    }


def compute_score(conditions: dict[str, bool]) -> int:
    """
    Compute the intraday score (0-10) from conditions.

    Scoring:
      - Green Candle: prerequisite (must be True for positive score)
      - Each other condition: +2 points

    Parameters
    ----------
    conditions : dict[str, bool]
        Output from evaluate_all_conditions()

    Returns
    -------
    int
        Score from 0 to 10
    """
    if not conditions.get("green_candle", False):
        return 0

    score = 0
    scoring_conditions = ["vwap", "ema", "rsi", "volume", "candle_breakout"]
    for cond in scoring_conditions:
        if conditions.get(cond, False):
            score += 2
    return score


def classify_action(score: int) -> str:
    """
    Classify the trading action based on score.

    Parameters
    ----------
    score : int
        Score from 0 to 10

    Returns
    -------
    str
        'BUY', 'WATCH', or 'AVOID'
    """
    if score >= BUY_THRESHOLD:
        return "BUY"
    elif score >= WATCH_THRESHOLD:
        return "WATCH"
    else:
        return "AVOID"


def get_comment(score: int, conditions: dict[str, bool]) -> str:
    """
    Generate a human-readable comment based on score and conditions.

    Parameters
    ----------
    score : int
        Computed score
    conditions : dict[str, bool]
        Evaluated conditions

    Returns
    -------
    str
        Brief comment string
    """
    if score >= BUY_THRESHOLD:
        parts = []
        if conditions.get("vwap"):
            parts.append("above VWAP")
        if conditions.get("volume"):
            parts.append("high volume")
        if conditions.get("rsi"):
            parts.append("strong momentum")
        return f"Strong {' + '.join(parts)}" if parts else "Strong setup"
    elif score >= WATCH_THRESHOLD:
        return "Building momentum, watch for confirmation"
    else:
        if not conditions.get("green_candle"):
            return "Red candle, avoid"
        return "Weak setup, insufficient signals"


if __name__ == "__main__":
    # Quick self-test
    test_data = {
        "Open": [100, 101, 102, 103, 104],
        "High": [102, 103, 104, 105, 106],
        "Low": [99, 100, 101, 102, 103],
        "Close": [101, 102, 103, 104, 105],
        "Volume": [10000, 12000, 15000, 11000, 25000],
    }
    df = pd.DataFrame(test_data)
    conds = evaluate_all_conditions(df)
    score = compute_score(conds)
    print(f"Conditions: {conds}")
    print(f"Score: {score}/10")
    print(f"Action: {classify_action(score)}")
    print(f"VWAP: {calculate_vwap(df).iloc[-1]:.2f}")
    print(f"EMA5: {calculate_ema(df, 5).iloc[-1]:.2f}")
    print(f"RSI: {calculate_rsi(df['Close']).iloc[-1]:.2f}")
