"""
config.py — Centralized Configuration
======================================
All configurable settings for the intraday scanner.
Values can be overridden via environment variables.
"""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

SCAN_RETRY_COUNT: int = int(os.getenv("SCAN_RETRY_COUNT", "1"))
SCAN_RATE_LIMIT_SECONDS: float = float(os.getenv("SCAN_RATE_LIMIT_SECONDS", "0.15"))
AUTO_REFRESH_INTERVAL_MS: int = int(os.getenv("AUTO_REFRESH_INTERVAL_MS", "60000"))
SCAN_TIMEOUT_SECONDS: int = int(os.getenv("SCAN_TIMEOUT_SECONDS", "45"))

TARGET_PCT: float = 1.015
STOPLOSS_PCT: float = 0.995

RSI_PERIOD: int = 14
RSI_MOMENTUM_THRESHOLD: float = 60.0
VOLUME_BREAKOUT_MULTIPLIER: float = 1.5

BUY_THRESHOLD: int = 8
WATCH_THRESHOLD: int = 6

MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MIN: int = 15
MARKET_CLOSE_HOUR: int = 15
MARKET_CLOSE_MIN: int = 30
IST_OFFSET_HOURS: int = 5
IST_OFFSET_MINUTES: int = 30
