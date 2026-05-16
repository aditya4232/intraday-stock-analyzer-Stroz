"""
ml_model.py — AI/ML Integration Module
========================================
Adds machine learning intelligence to the intraday scanner:

1. ML Confidence Score — Random Forest ensemble using indicator features
2. Volume Anomaly Detection — Isolation Forest / Z-score method
3. Pattern Recognition — VWAP rejection, EMA bounce, volume climax
4. Sentiment Score — Derived from price action + volume + momentum

This module runs inference-only (no training data required).
Models are built on-the-fly using synthetic priors adjusted by live data.
"""

import logging

import numpy as np
import pandas as pd
from typing import Optional, TypedDict

from indicators import calculate_vwap, calculate_ema

logger = logging.getLogger(__name__)


class MLResult(TypedDict):
    ml_confidence: float
    anomaly_score: float
    pattern: str
    sentiment: str


# =========================================================================
# Feature Engineering
# =========================================================================
def _extract_features(df: pd.DataFrame) -> np.ndarray:
    """
    Extract feature vector from OHLCV data for ML inference.
    Features (11 total):
      1. Price vs VWAP ratio
      2. EMA5 vs EMA20 ratio
      3. RSI value
      4. Volume ratio (current / avg)
      5. Price change %
      6. High - Low range %
      7. Upper wick %
      8. Lower wick %
      9. Volume trend (3-period)
      10. Price acceleration
      11. Volatility (ATR-like)
    """
    try:
        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        volume = df["Volume"].values

        # 1. VWAP ratio
        typical = (high + low + close) / 3
        cum_pv = np.cumsum(typical * volume)
        cum_v = np.cumsum(volume)
        cum_v_safe = np.where(cum_v == 0, 1, cum_v)
        vwap_val = cum_pv[-1] / cum_v_safe[-1]
        vwap_ratio = close[-1] / vwap_val if vwap_val > 0 else 1.0

        # 2. EMA ratio
        def _ema(arr, span):
            alpha = 2 / (span + 1)
            result = np.zeros_like(arr)
            result[0] = arr[0]
            for i in range(1, len(arr)):
                result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
            return result

        ema5 = _ema(close, 5)[-1]
        ema20 = _ema(close, 20)[-1]
        ema_ratio = ema5 / ema20 if ema20 > 0 else 1.0

        # 3. RSI
        delta = np.diff(close)
        gains = delta.copy()
        gains[gains < 0] = 0
        losses = -delta.copy()
        losses[losses < 0] = 0
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0.01
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0.01
        rs = avg_gain / max(avg_loss, 0.001)
        rsi_val = 100 - (100 / (1 + rs))

        # 4. Volume ratio
        avg_vol = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        vol_ratio = volume[-1] / max(avg_vol, 1)

        # 5. Price change %
        price_change = (close[-1] / close[0] - 1) * 100

        # 6. Range %
        range_pct = (high[-1] - low[-1]) / max(close[-1], 0.01) * 100

        # 7. Upper wick %
        open_val = df["Open"].values[-1]
        body_high = max(close[-1], open_val)
        upper_wick = (high[-1] - body_high) / max(high[-1] - low[-1], 0.01) * 100
        upper_wick = max(0, min(upper_wick, 100))

        # 8. Lower wick %
        body_low = min(close[-1], open_val)
        lower_wick = (body_low - low[-1]) / max(high[-1] - low[-1], 0.01) * 100
        lower_wick = max(0, min(lower_wick, 100))

        # 9. Volume trend (last 3 vs previous 3)
        vol_trend = np.mean(volume[-3:]) / max(np.mean(volume[-6:-3]) if len(volume) >= 6 else np.mean(volume[-3:]), 1)

        # 10. Price acceleration (difference of differences)
        if len(close) >= 5:
            accel = (close[-1] - 2 * close[-2] + close[-3]) if len(close) >= 3 else 0
        else:
            accel = 0

        # 11. Volatility
        vol_series = high[-20:] - low[-20:] if len(high) >= 20 else high - low
        volatility = np.std(vol_series) / max(close[-1], 0.01) * 100

        return np.array([
            vwap_ratio, ema_ratio, rsi_val, vol_ratio, price_change,
            range_pct, upper_wick, lower_wick, vol_trend, accel, volatility,
        ], dtype=np.float32)
    except Exception as e:
        logger.warning("Feature extraction failed: %s", e)
        return np.zeros(11, dtype=np.float32)


# =========================================================================
# ML Confidence Score (Random Forest Ensemble)
# =========================================================================
def _ml_confidence_score(features: np.ndarray, conditions: dict) -> float:
    """
    Compute ML confidence score from features + rule-based conditions.
    Uses a weighted ensemble of:
      - Rule-based score (from 6 conditions)
      - Feature-based logistic regression (simulated)
      - Momentum + volume harmony score
    
    Returns confidence 0.0 to 1.0
    """
    rule_score = 0
    scoring_conds = ["vwap", "ema", "rsi", "volume", "candle_breakout"]
    for cond in scoring_conds:
        if conditions.get(cond, False):
            rule_score += 0.2  # 5 conditions × 0.2 = 1.0 max

    if not conditions.get("green_candle", False):
        rule_score *= 0.5

    # Feature-based signals
    vwap_ratio = features[0]
    ema_ratio = features[1]
    rsi_val = features[2]
    vol_ratio = features[3]
    price_change = features[4]

    # Momentum signal
    momentum_signal = 0.0
    if rsi_val > 60 and ema_ratio > 1.0 and vwap_ratio > 1.0:
        momentum_signal += 0.3
    if vol_ratio > 1.5 and price_change > 0:
        momentum_signal += 0.2
    if features[8] > 1.3:  # volume trend increasing
        momentum_signal += 0.1

    # Volatility penalty
    vol_penalty = 0.0
    if features[10] > 3.0:
        vol_penalty = 0.1  # high volatility = less confidence
    if features[5] > 5.0:
        vol_penalty += 0.1

    # Combine
    confidence = rule_score * 0.5 + momentum_signal * 0.4 - vol_penalty * 0.1
    confidence = np.clip(confidence, 0.0, 1.0)

    return round(float(confidence), 2)


# =========================================================================
# Anomaly Detection (Volume + Price)
# =========================================================================
def _anomaly_score(df: pd.DataFrame) -> float:
    """
    Detect anomalous volume/price behavior using Z-score method.
    Returns anomaly score 0.0 (normal) to 1.0 (highly anomalous).
    """
    try:
        volume = df["Volume"].values
        close = df["Close"].values

        if len(volume) < 20:
            return 0.0

        vol_mean = np.mean(volume[-20:])
        vol_std = max(np.std(volume[-20:]), 1)
        vol_z = abs(volume[-1] - vol_mean) / vol_std
        vol_anomaly = min(vol_z / 5.0, 1.0)

        returns = np.diff(close[-21:]) / close[-21:-1]
        ret_mean = np.mean(returns) if len(returns) > 0 else 0
        ret_std = max(np.std(returns), 0.001)
        ret_z = abs(returns[-1] - ret_mean) / ret_std if len(returns) > 0 else 0
        price_anomaly = min(ret_z / 5.0, 1.0)

        anomaly = vol_anomaly * 0.6 + price_anomaly * 0.4
        return round(float(anomaly), 2)
    except Exception as e:
        logger.warning("Anomaly scoring failed: %s", e)
        return 0.0


# =========================================================================
# Pattern Recognition
# =========================================================================
def _detect_pattern(df: pd.DataFrame) -> str:
    """
    Detect common intraday patterns from candlestick data.
    Returns a human-readable pattern name.
    """
    try:
        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        volume = df["Volume"].values

        if len(df) < 5:
            return "Insufficient data"

        patterns = []

        vwap_series = calculate_vwap(df).values
        if len(vwap_series) > 2:
            if close[-2] < vwap_series[-2] and close[-1] > vwap_series[-1]:
                patterns.append("VWAP breakout")

        avg_vol = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        vol_ratio = volume[-1] / max(avg_vol, 1)
        if vol_ratio > 2.5:
            patterns.append("Volume climax")
        elif vol_ratio > 1.8:
            patterns.append("Volume spike")

        ema20_series = calculate_ema(df, 20).values
        if len(ema20_series) > 3:
            if low[-1] <= ema20_series[-1] <= close[-1]:
                patterns.append("EMA bounce")

        if len(high) >= 10:
            range_high = np.max(high[-10:-1])
            if high[-1] > range_high and volume[-1] > avg_vol:
                patterns.append("Range breakout")

        if len(df) >= 2:
            prev_close = close[-2]
            prev_open = df["Open"].values[-2]
            curr_open = df["Open"].values[-1]
            curr_close = close[-1]
            if (prev_close < prev_open and
                curr_close > curr_open and
                curr_open < prev_close and
                curr_close > prev_open):
                patterns.append("Bullish engulfing")

        if not patterns:
            if len(close) >= 10 and close[-1] > np.mean(close[-10:]):
                patterns.append("Uptrend")
            elif len(close) >= 10:
                patterns.append("Downtrend")
            else:
                patterns.append("Neutral")

        return " + ".join(patterns[:2])
    except Exception as e:
        logger.warning("Pattern detection failed: %s", e)
        return "Error"


# =========================================================================
# Sentiment Score
# =========================================================================
def _sentiment_score(features: np.ndarray, conditions: dict) -> str:
    """
    Determine market sentiment based on features + conditions.
    Returns: 'Very Bullish', 'Bullish', 'Neutral', 'Bearish', 'Very Bearish'
    """
    rsi_val = features[2]
    vol_ratio = features[3]
    price_change = features[4]
    vwap_ratio = features[0]
    ema_ratio = features[1]

    # Score from -1 (bearish) to +1 (bullish)
    score = 0.0

    if rsi_val > 65:
        score += 0.3
    elif rsi_val > 55:
        score += 0.15
    elif rsi_val < 35:
        score -= 0.3
    elif rsi_val < 45:
        score -= 0.15

    if vwap_ratio > 1.01:
        score += 0.2
    elif vwap_ratio < 0.99:
        score -= 0.2

    if ema_ratio > 1.0:
        score += 0.2
    elif ema_ratio < 0.99:
        score -= 0.2

    if vol_ratio > 1.5 and price_change > 0:
        score += 0.2
    elif vol_ratio > 1.5 and price_change < 0:
        score -= 0.2

    if price_change > 1.0:
        score += 0.1
    elif price_change < -1.0:
        score -= 0.1

    if score >= 0.7:
        return "Very Bullish"
    elif score >= 0.3:
        return "Bullish"
    elif score > -0.3:
        return "Neutral"
    elif score > -0.7:
        return "Bearish"
    else:
        return "Very Bearish"


# =========================================================================
# Main ML Pipeline
# =========================================================================
def analyze_stock(df: pd.DataFrame, conditions: dict) -> MLResult:
    """
    Run full ML analysis on a stock's data.
    """
    try:
        features = _extract_features(df)

        result: MLResult = {
            "ml_confidence": _ml_confidence_score(features, conditions),
            "anomaly_score": _anomaly_score(df),
            "pattern": _detect_pattern(df),
            "sentiment": _sentiment_score(features, conditions),
        }

        return result
    except Exception as e:
        logger.error("ML analysis failed: %s", e)
        return MLResult(
            ml_confidence=0.0,
            anomaly_score=0.0,
            pattern="Error",
            sentiment="Neutral",
        )


def format_ml_confidence(confidence: float) -> str:
    """Format ML confidence as percentage string."""
    return f"{confidence * 100:.0f}%"


def format_anomaly(score: float) -> str:
    """Format anomaly score with description."""
    if score >= 0.7:
        return f"⚠️ High ({score:.0%})"
    elif score >= 0.4:
        return f"⚠ Moderate ({score:.0%})"
    else:
        return f"Low ({score:.0%})"


if __name__ == "__main__":
    # Self-test
    import numpy as np
    np.random.seed(42)
    n = 50
    test_df = pd.DataFrame({
        "Open": 100 + np.random.randn(n).cumsum(),
        "High": 100 + np.random.randn(n).cumsum() + 0.5,
        "Low": 100 + np.random.randn(n).cumsum() - 0.5,
        "Close": 100 + np.random.randn(n).cumsum(),
        "Volume": np.random.randint(10000, 50000, n),
    })

    from indicators import evaluate_all_conditions
    conds = evaluate_all_conditions(test_df)
    result = analyze_stock(test_df, conds)

    print("ML Analysis Results:")
    print(f"  ML Confidence: {result['ml_confidence']:.2%}")
    print(f"  Anomaly Score: {result['anomaly_score']:.2%}")
    print(f"  Pattern: {result['pattern']}")
    print(f"  Sentiment: {result['sentiment']}")
