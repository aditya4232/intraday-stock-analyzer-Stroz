"""
scraper.py — ScrapeGraphAI Real-Time NSE Market Data Scraper
==============================================================

Uses the official ScrapeGraphAI library to implement a graph-based
scraping pipeline for live NSE stock market data.

ScrapeGraphAI provides:
  - SmartScraperGraph:  AI-powered scraping of any web page using LLMs
  - SearchGraph: Web search + scrape pipeline
  - Graph-based execution: Nodes connected by edges in a DAG

Architecture:
  SmartScraperGraph (Google Finance) + yfinance (primary data)
    -> ParseNode (extract structured records)
    -> EnrichNode (add sector, Nifty 50 membership)
    -> AggregateNode (produce DataFrames)

LLM Configuration (via .env):
  SCRAPE_LLM_MODEL=gpt-4o          # or ollama/llama3, gemini/gemini-pro
  SCRAPE_LLM_API_KEY=your-key-here  # not needed for ollama
  SCRAPE_LLM_PROVIDER=openai        # openai, ollama, gemini, azure

When no LLM is configured, falls back to:
  1. BeautifulSoup-based direct scraping
  2. yfinance API (fastest for NSE data)
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import SCAN_RATE_LIMIT_SECONDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ScrapeGraphAI Configuration
# ---------------------------------------------------------------------------
# Load LLM config from environment (with sensible defaults for local/Ollama)
SCRAPE_LLM_MODEL = os.getenv("SCRAPE_LLM_MODEL", "")
SCRAPE_LLM_API_KEY = os.getenv("SCRAPE_LLM_API_KEY", "")
# Default provider is empty so that open-source fallbacks are primary
SCRAPE_LLM_PROVIDER = os.getenv("SCRAPE_LLM_PROVIDER", "")

# ScrapeGraphAI Cloud API key (format: sgai-...)
# When set, the library uses ScrapeGraphAI's cloud service instead of a local LLM.
# Leave unset by default; treat ScrapeGraphAI as a fallback when explicitly configured.
SCRAPEGRAPHAI_CLOUD_API_KEY = os.getenv("SCRAPEGRAPHAI_CLOUD_API_KEY", "")

_HAS_SGAI = False
try:
    from scrapegraphai.graphs import SmartScraperGraph, SearchGraph
    _HAS_SGAI = True
except ImportError:
    logger.warning("scrapegraphai not installed — using fallback scrapers")
    SmartScraperGraph = None
    SearchGraph = None


def _build_sgai_config() -> dict | None:
    """Build ScrapeGraphAI config dict based on environment settings.

    Supports:
      - ScrapeGraphAI Cloud (api_key starting with 'sgai-')
      - OpenAI
      - Ollama (local, no API key needed)
      - Gemini

    Returns None if no valid LLM configuration is available.
    """
    cloud_api_key = SCRAPEGRAPHAI_CLOUD_API_KEY.strip()
    model = SCRAPE_LLM_MODEL.strip()
    api_key = SCRAPE_LLM_API_KEY.strip()
    provider = SCRAPE_LLM_PROVIDER.strip().lower()

    # Prefer open-source fallback (no LLM configured) unless explicit cloud/provider config present
    # --- ScrapeGraphAI Cloud (only if explicitly configured) ---
    if cloud_api_key:
        logger.info("Using ScrapeGraphAI Cloud API")
        return {
            "api_key": cloud_api_key,
            "llm": {
                "model": model or "gpt-4o",
                "temperature": 0.1,
            },
        }

    # --- ScrapeGraphAI Cloud via SCRAPE_LLM_API_KEY with sgai- prefix (explicit) ---
    if api_key.startswith("sgai-"):
        logger.info("Using ScrapeGraphAI Cloud API (via SCRAPE_LLM_API_KEY)")
        return {
            "api_key": api_key,
            "llm": {
                "model": model or "gpt-4o",
                "temperature": 0.1,
            },
        }

    # --- Ollama default (only if SCRAPE_LLM_PROVIDER explicitly set to 'ollama') ---
    if provider == "ollama":
        # fall back to local Ollama if requested
        model = model or "ollama/llama3"
        return {
            "llm": {
                "model": model,
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "temperature": 0.1,
            },
        }

    # --- No model configured ---
    if not model:
        return None

    # --- OpenAI ---
    if provider == "openai":
        return {
            "llm": {
                "model": model,
                "api_key": api_key or os.getenv("OPENAI_API_KEY", ""),
                "temperature": 0.1,
            },
        }
    # --- Ollama (explicit) ---
    elif provider == "ollama":
        return {
            "llm": {
                "model": model,
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "temperature": 0.1,
            },
        }
    # --- Gemini ---
    elif provider == "gemini":
        return {
            "llm": {
                "model": model,
                "api_key": api_key or os.getenv("GEMINI_API_KEY", ""),
                "temperature": 0.1,
            },
        }
    else:
        logger.warning("Unknown LLM provider '%s' — disabling ScrapeGraphAI", provider)
        return None


# =============================================================================
# ScrapeGraphAI-powered stock price scraper
# =============================================================================
def _scrape_google_finance_sgai(symbol: str) -> dict | None:
    """
    Use ScrapeGraphAI's SmartScraperGraph to scrape live stock data
    from Google Finance.

    Parameters
    ----------
    symbol : str
        NSE symbol (e.g., 'HDFCBANK')

    Returns
    -------
    dict or None
        Extracted data with keys like 'price', 'change', 'change_percent', etc.
    """
    if not _HAS_SGAI or SmartScraperGraph is None:
        return None

    config = _build_sgai_config()
    if config is None:
        logger.debug("No LLM configured — skipping ScrapeGraphAI scrape")
        return None

    url = f"https://www.google.com/finance/quote/{symbol}:NSE"

    prompt = (
        f"Extract the current stock price data for {symbol} from this Google Finance page. "
        f"Return ONLY valid JSON with these exact keys: "
        f"price (number), change (number), change_percent (number), "
        f"previous_close (number), market_cap (string), name (string). "
        f"Do not include any explanation, just the JSON object."
    )

    try:
        graph = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=config,
        )
        result = graph.run()
        if result and isinstance(result, dict):
            return result
        if result and isinstance(result, str):
            return json.loads(result)
        return None
    except Exception as e:
        logger.debug("ScrapeGraphAI scrape failed for %s: %s", symbol, e)
        return None


def _scrape_google_finance_bs4(symbol: str) -> dict | None:
    """
    Fallback: scrape Google Finance using BeautifulSoup (no LLM needed).

    Parameters
    ----------
    symbol : str
        NSE symbol (e.g., 'HDFCBANK')

    Returns
    -------
    dict or None
        Extracted stock data
    """
    try:
        url = f"https://www.google.com/finance/quote/{symbol}:NSE"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        data = {}

        # Try to extract price from multiple possible selectors
        price_div = soup.find("div", {"data-last-price": True})
        if price_div:
            data["price"] = float(price_div["data-last-price"])

        # Try common Google Finance price element selectors
        for selector in [
            "div.YMlKec.fxKbKc",
            ".YMlKec",
            "[jsname='LgbsSe']",
        ]:
            elem = soup.select_one(selector)
            if elem:
                try:
                    text = elem.text.strip().replace(",", "").replace("₹", "")
                    data["price"] = float(text)
                    break
                except (ValueError, AttributeError):
                    continue

        # Company name
        company_elem = soup.select_one("div.zzDege")
        if company_elem:
            data["name"] = company_elem.text.strip()

        # Change
        change_elem = soup.select_one("div.P6K39c")
        if change_elem:
            text = change_elem.text.strip()
            # Parse "₹-12.45 (-0.35%)" or similar
            import re
            match = re.search(r"([+-]?[\d,.]+)\s*\(([+-]?[\d.]+)%\)", text)
            if match:
                data["change"] = float(match.group(1).replace(",", ""))
                data["change_percent"] = float(match.group(2))

        return data if data else None

    except Exception as e:
        logger.debug("BS4 scrape failed for %s: %s", symbol, e)
        return None


def scrape_live_price(symbol: str) -> dict | None:
    """
    Scrape live stock price data using ScrapeGraphAI (primary)
    with BeautifulSoup fallback.

    Pipeline:
      1. Try ScrapeGraphAI SmartScraperGraph (if LLM is configured)
      2. Fallback to BeautifulSoup direct scraping
      3. Returns dict with price, change, etc. or None

    Parameters
    ----------
    symbol : str
        NSE symbol (e.g., 'HDFCBANK')

    Returns
    -------
    dict or None
        {'price': float, 'change': float, 'change_percent': float, ...} or None
    """
    # Prefer open-source scraping (BeautifulSoup) as primary to avoid cloud rate limits.
    # If ScrapeGraphAI is explicitly configured (cloud key or provider), it will be used as a fallback.

    # Step 1: Try BeautifulSoup fallback (free, unlimited)
    try:
        result_bs4 = _scrape_google_finance_bs4(symbol)
        if result_bs4 and "price" in result_bs4:
            logger.info("BS4 scraped %s: price=%s", symbol, result_bs4.get("price"))
            return result_bs4
    except Exception as e:
        logger.debug("BS4 scraper failed for %s: %s", symbol, e)

    # Step 2: If BS4 failed, and ScrapeGraphAI is available and explicitly configured, try it
    try:
        config = _build_sgai_config()
        if _HAS_SGAI and config is not None:
            result_sgai = _scrape_google_finance_sgai(symbol)
            if result_sgai and "price" in result_sgai:
                logger.info("ScrapeGraphAI scraped %s: price=%s", symbol, result_sgai.get("price"))
                return result_sgai
    except Exception as e:
        logger.debug("ScrapeGraphAI scraper failed for %s: %s", symbol, e)

    # Nothing succeeded
    return None


def batch_scrape_live_prices(symbols: list[str]) -> dict[str, dict]:
    """
    Scrape live prices for multiple symbols.

    Parameters
    ----------
    symbols : list of str
        List of NSE symbols (without .NS suffix)

    Returns
    -------
    dict[str, dict]
        Mapping of symbol -> scraped data dict
    """
    results = {}
    for sym in symbols:
        data = scrape_live_price(sym)
        if data:
            results[sym] = data
    return results


# =============================================================================
# ScrapeGraphAI-powered company info scraper
# =============================================================================
def scrape_company_info(symbol: str) -> dict | None:
    """
    Use ScrapeGraphAI's SearchGraph to find company information
    by searching the web.

    Requires an LLM to be configured. Falls back to basic info otherwise.

    Parameters
    ----------
    symbol : str
        NSE symbol

    Returns
    -------
    dict or None
        Company info with keys like name, sector, industry, description
    """
    if not _HAS_SGAI or SearchGraph is None:
        return None

    config = _build_sgai_config()
    if config is None:
        return None

    prompt = (
        f"Search the web for information about the company with NSE stock ticker {symbol}. "
        f"Return ONLY valid JSON with these exact keys: "
        f"name (string), sector (string), industry (string), description (string). "
        f"Do not include any explanation."
    )

    try:
        graph = SearchGraph(
            prompt=prompt,
            config=config,
        )
        result = graph.run()
        # SearchGraph returns a string; try to parse as JSON
        if result:
            import json as _json
            try:
                return _json.loads(result) if isinstance(result, str) else result
            except (_json.JSONDecodeError, TypeError):
                logger.debug("SearchGraph returned non-JSON for %s", symbol)
        return None
    except Exception as e:
        logger.debug("SearchGraph failed for %s: %s", symbol, e)
        return None


# =============================================================================
# Custom ScrapeGraphAI-style Graph Nodes (fallback when LLM not available)
# =============================================================================
# These implement the same ScrapeGraphAI architecture concepts but work
# without requiring an LLM. They're used when no LLM configuration is set.

from abc import ABC, abstractmethod


class GraphNode(ABC):
    """Base class for ScrapeGraphAI-style graph nodes (fallback)."""

    def __init__(self, name: str):
        self.name = name
        self._edges: list["GraphEdge"] = []

    def add_edge(self, edge: "GraphEdge") -> None:
        self._edges.append(edge)

    @abstractmethod
    def execute(self, state: dict) -> dict:
        ...


class GraphEdge:
    """Connects two nodes in the scraping graph."""

    def __init__(self, source: GraphNode, target: GraphNode, condition=None):
        self.source = source
        self.target = target
        self.condition = condition


class ScrapeGraph:
    """
    Custom ScrapeGraphAI-style graph orchestrator (fallback).
    Mirrors the ScrapeGraphAI graph execution model.
    """

    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._entry_node: Optional[GraphNode] = None

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.name] = node
        if self._entry_node is None:
            self._entry_node = node

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)
        edge.source.add_edge(edge)

    def set_entry_point(self, node: GraphNode) -> None:
        self._entry_node = node

    def run(self, initial_state: dict | None = None) -> dict:
        state = initial_state or {}
        visited = set()
        queue = [self._entry_node]

        while queue:
            node = queue.pop(0)
            if node.name in visited:
                continue
            visited.add(node.name)

            try:
                state = node.execute(state)
            except Exception as e:
                logger.error("Node '%s' failed: %s", node.name, e)
                state[f"{node.name}_error"] = str(e)
                continue

            for edge in node._edges:
                if edge.condition is None or edge.condition(state):
                    if edge.target not in queue:
                        queue.append(edge.target)

        return state


class SearchNode(GraphNode):
    """Resolves stock symbols and their metadata."""

    def __init__(self):
        super().__init__("SearchNode")

    def execute(self, state: dict) -> dict:
        from stocks_db import NSE_STOCKS, STOCK_SECTORS, NIFTY50_SYMBOLS

        symbols = state.get("symbols", [])
        sector = state.get("sector", "All Sectors")

        if not symbols and sector:
            symbols = NSE_STOCKS.get(sector, [])

        stock_meta = []
        for sym in symbols:
            raw = sym.replace(".NS", "")
            meta = {
                "symbol": sym,
                "raw_symbol": raw,
                "sector": STOCK_SECTORS.get(raw, "Unknown"),
                "is_nifty50": raw in NIFTY50_SYMBOLS,
            }
            stock_meta.append(meta)

        state["stock_meta"] = stock_meta
        state["total_stocks"] = len(stock_meta)
        return state


class FetchNode(GraphNode):
    """
    FetchNode: Downloads real-time market data.
    Uses yfinance as primary, with web scraping fallback.
    """

    def __init__(self):
        super().__init__("FetchNode")

    def execute(self, state: dict) -> dict:
        import yfinance as yf
        import time

        stock_meta = state.get("stock_meta", [])
        raw_data = {}
        errors = []

        for meta in stock_meta:
            symbol = meta["symbol"]
            raw_symbol = meta["raw_symbol"]

            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="5d", interval="5m")

                if df is None or df.empty:
                    # Fallback: scrape live price
                    price_data = scrape_live_price(raw_symbol)
                    if price_data and "price" in price_data:
                        # Construct minimal DataFrame
                        now = datetime.now()
                        df = pd.DataFrame(
                            {
                                "Open": [price_data["price"]],
                                "High": [price_data["price"] * 1.005],
                                "Low": [price_data["price"] * 0.995],
                                "Close": [price_data["price"]],
                                "Volume": [0],
                            },
                            index=[now],
                        )
                    else:
                        errors.append({"symbol": symbol, "error": "No data from yfinance or web scrape"})
                        continue

                # Flatten MultiIndex columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [" ".join(col).strip() for col in df.columns]
                    rename_map = {}
                    for col in df.columns:
                        cl = col.lower()
                        if "open" in cl: rename_map[col] = "Open"
                        elif "high" in cl: rename_map[col] = "High"
                        elif "low" in cl: rename_map[col] = "Low"
                        elif "close" in cl: rename_map[col] = "Close"
                        elif "volume" in cl: rename_map[col] = "Volume"
                    df = df.rename(columns=rename_map)

                required = ["Open", "High", "Low", "Close", "Volume"]
                if not all(c in df.columns for c in required):
                    errors.append({"symbol": symbol, "error": "Missing required columns"})
                    continue

                df.attrs["symbol"] = raw_symbol
                df.attrs["sector"] = meta["sector"]
                df.attrs["is_nifty50"] = meta["is_nifty50"]
                raw_data[symbol] = df

            except Exception as e:
                logger.warning("FetchNode failed for %s: %s", symbol, e)
                errors.append({"symbol": symbol, "error": str(e)})
                continue
            finally:
                time.sleep(SCAN_RATE_LIMIT_SECONDS)

        state["raw_dataframes"] = raw_data
        state["fetch_errors"] = errors
        state["fetched_count"] = len(raw_data)
        return state


class ParseNode(GraphNode):
    """Extracts structured data from raw DataFrames."""

    def __init__(self):
        super().__init__("ParseNode")

    def execute(self, state: dict) -> dict:
        raw_data = state.get("raw_dataframes", {})
        records = []

        for symbol, df in raw_data.items():
            try:
                latest = df.iloc[-1]
                record = {
                    "symbol": df.attrs.get("symbol", symbol.replace(".NS", "")),
                    "sector": df.attrs.get("sector", "Unknown"),
                    "is_nifty50": df.attrs.get("is_nifty50", False),
                    "ltp": float(latest["Close"]),
                    "open": float(latest["Open"]),
                    "high": float(latest["High"]),
                    "low": float(latest["Low"]),
                    "volume": int(latest["Volume"]),
                    "price_change_pct": (
                        (float(latest["Close"]) / float(df["Open"].iloc[0]) - 1) * 100
                    ),
                    "data_points": len(df),
                    "timestamp": datetime.now(),
                }
                records.append(record)
            except Exception as e:
                logger.warning("ParseNode error for %s: %s", symbol, e)
                continue

        state["parsed_records"] = records
        state["parsed_count"] = len(records)
        return state


class EnrichNode(GraphNode):
    """Enriches parsed data with sector/Nifty 50 context."""

    def __init__(self):
        super().__init__("EnrichNode")

    def execute(self, state: dict) -> dict:
        records = state.get("parsed_records", [])
        enriched = []

        for record in records:
            enriched_record = {
                **record,
                "sector_display": record["sector"],
                "index_membership": "NIFTY 50" if record["is_nifty50"] else "Broader Market",
                "market_cap_tier": "Large Cap" if record["is_nifty50"] else "Mid/Small Cap",
            }
            enriched.append(enriched_record)

        # Sector-wise summary
        sector_summary: dict[str, dict] = {}
        for rec in enriched:
            sec = rec["sector"]
            if sec not in sector_summary:
                sector_summary[sec] = {"count": 0, "nifty50_count": 0, "avg_price_change": 0.0, "stocks": []}
            sector_summary[sec]["count"] += 1
            if rec["is_nifty50"]:
                sector_summary[sec]["nifty50_count"] += 1
            sector_summary[sec]["avg_price_change"] += rec["price_change_pct"]
            sector_summary[sec]["stocks"].append(rec["symbol"])

        for sec, data in sector_summary.items():
            data["avg_price_change"] = round(data["avg_price_change"] / max(data["count"], 1), 2)

        state["enriched_records"] = enriched
        state["sector_summary"] = sector_summary
        state["enriched_count"] = len(enriched)
        return state


class AggregateNode(GraphNode):
    """Aggregates enriched data into final output formats."""

    def __init__(self):
        super().__init__("AggregateNode")

    def execute(self, state: dict) -> dict:
        records = state.get("enriched_records", [])
        sector_summary = state.get("sector_summary", {})

        if not records:
            state["results_dataframe"] = pd.DataFrame()
            state["sector_dataframe"] = pd.DataFrame()
            state["nifty50_vs_broader"] = {"nifty50": 0, "broader": 0}
            return state

        df = pd.DataFrame(records)

        sector_rows = []
        for sec, data in sector_summary.items():
            sector_rows.append({
                "Sector": sec,
                "Total Stocks": data["count"],
                "Nifty 50": data["nifty50_count"],
                "Broader Market": data["count"] - data["nifty50_count"],
                "Avg Change %": data["avg_price_change"],
            })
        sector_df = pd.DataFrame(sector_rows)
        sector_df = sector_df.sort_values("Total Stocks", ascending=False).reset_index(drop=True)

        nifty50_count = sum(1 for r in records if r["is_nifty50"])
        broader_count = len(records) - nifty50_count

        state["results_dataframe"] = df
        state["sector_dataframe"] = sector_df
        state["nifty50_vs_broader"] = {"nifty50": nifty50_count, "broader": broader_count}
        return state


# =============================================================================
# Graph Builder
# =============================================================================

def build_scraper_graph() -> ScrapeGraph:
    """
    Build and return a configured ScrapeGraphAI-style scraping graph.

    Graph topology:
        SearchNode -> FetchNode -> ParseNode -> EnrichNode -> AggregateNode

    Note: When ScrapeGraphAI's SmartScraperGraph is available and configured
    with an LLM, this graph is enhanced with AI-powered web scraping.

    Returns
    -------
    ScrapeGraph
        A fully connected scraping graph ready for execution.
    """
    graph = ScrapeGraph()

    search_node = SearchNode()
    fetch_node = FetchNode()
    parse_node = ParseNode()
    enrich_node = EnrichNode()
    aggregate_node = AggregateNode()

    graph.add_node(search_node)
    graph.add_node(fetch_node)
    graph.add_node(parse_node)
    graph.add_node(enrich_node)
    graph.add_node(aggregate_node)

    graph.add_edge(GraphEdge(search_node, fetch_node))
    graph.add_edge(GraphEdge(fetch_node, parse_node))
    graph.add_edge(GraphEdge(parse_node, enrich_node))
    graph.add_edge(GraphEdge(enrich_node, aggregate_node))

    graph.set_entry_point(search_node)
    return graph


# =============================================================================
# Convenience Functions
# =============================================================================

def scrape_nse_data(
    sector: str = "All Sectors",
    symbols: list[str] | None = None,
) -> dict:
    """
    Run the full scraping pipeline in one call.

    Uses ScrapeGraphAI-powered web scraping when available,
    falling back to yfinance + BeautifulSoup.

    Parameters
    ----------
    sector : str
        Sector to scrape (from stocks_db.get_sectors()).
    symbols : list[str] | None
        Optional explicit symbol list.

    Returns
    -------
    dict with keys: results_dataframe, sector_dataframe,
                    nifty50_vs_broader, sector_summary, fetched_count
    """
    graph = build_scraper_graph()
    initial_state = {}
    if symbols:
        initial_state["symbols"] = symbols
    else:
        initial_state["sector"] = sector

    final_state = graph.run(initial_state)

    # Log if ScrapeGraphAI LLM is being used
    if _HAS_SGAI and _build_sgai_config() is not None:
        logger.info("ScrapeGraphAI LLM scraping is active (model: %s)", SCRAPE_LLM_MODEL or "ollama/llama3")

    return final_state


def is_scrapegraphai_available() -> bool:
    """
    Check if ScrapeGraphAI is installed AND configured with an LLM.

    Returns
    -------
    bool
        True if ScrapeGraphAI AI-powered scraping is available
    """
    return _HAS_SGAI and _build_sgai_config() is not None


def get_scrapegraphai_status() -> str:
    """
    Get a human-readable status of the ScrapeGraphAI integration.

    Returns
    -------
    str
        Status description
    """
    if not _HAS_SGAI:
        return "Not installed (pip install scrapegraphai)"

    # Check for cloud API key first
    cloud_key = SCRAPEGRAPHAI_CLOUD_API_KEY.strip()
    if cloud_key:
        masked_key = cloud_key[:8] + "..." + cloud_key[-4:] if len(cloud_key) > 15 else "configured"
        return f"Cloud Active (key: {masked_key})"

    # Check for sgai- prefixed key in SCRAPE_LLM_API_KEY
    if SCRAPE_LLM_API_KEY.strip().startswith("sgai-"):
        return "Cloud Active (via SCRAPE_LLM_API_KEY)"

    config = _build_sgai_config()
    if config is None:
        return "Installed but no LLM configured (set SCRAPEGRAPHAI_CLOUD_API_KEY or SCRAPE_LLM_MODEL)"
    provider = SCRAPE_LLM_PROVIDER or "ollama"
    model = SCRAPE_LLM_MODEL or "ollama/llama3"
    return f"Active ({provider}: {model})"


# =============================================================================
# ScrapeGraphAI-powered NSE Index Scraper
# =============================================================================
def scrape_nifty50_live_data() -> list[dict] | None:
    """
    Fetch live Nifty 50 index data using ScrapeGraphAI's SmartScraperGraph
    (for HTML scraping) or direct API call for the NSE JSON endpoint.

    Returns a list of dicts with constituent stock data, or None on failure.

    This demonstrates ScrapeGraphAI's ability to scrape financial data
    with AI-powered extraction.
    """
    # First try: direct NSE API call (most reliable)
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        resp = requests.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data:
                return [
                    {
                        "symbol": item.get("symbol", ""),
                        "company_name": item.get("meta", {}).get("companyName", ""),
                        "last_price": item.get("lastPrice", 0),
                        "change": item.get("change", 0),
                        "change_percent": item.get("pChange", 0),
                    }
                    for item in data["data"]
                ]
    except Exception as e:
        logger.debug("NSE API direct call failed: %s", e)

    # Second try: ScrapeGraphAI SmartScraperGraph with LLM
    if not _HAS_SGAI or SmartScraperGraph is None:
        return None

    config = _build_sgai_config()
    if config is None:
        return None

    prompt = (
        "Extract the Nifty 50 index constituents and their current data "
        "from this NSE India page. Return a JSON array of objects with keys: "
        "symbol (string), company_name (string), last_price (number), "
        "change (number), change_percent (number). "
        "Return ONLY the JSON array, no other text."
    )

    try:
        graph = SmartScraperGraph(
            prompt=prompt,
            source="https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
            config=config,
        )
        result = graph.run()
        if result:
            return result if isinstance(result, list) else [result]
        return None
    except Exception as e:
        logger.debug("ScrapeGraphAI Nifty 50 scrape failed: %s", e)
        return None


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("ScrapeGraphAI NSE Scraper — Self Test")
    print("=" * 60)

    print(f"\nScrapeGraphAI Status: {get_scrapegraphai_status()}")
    print(f"Library available: {_HAS_SGAI}")

    # Test custom graph
    print("\n--- Testing custom ScrapeGraph (fallback) ---")
    result = scrape_nse_data("Banking")
    df = result.get("results_dataframe", pd.DataFrame())
    print(f"Graph pipeline: {result.get('fetched_count', 0)} stocks fetched")
    if not df.empty:
        print(f"Sample: {df[['symbol', 'sector', 'ltp']].head(3).to_string()}")

    # Test web scraper (only if LLM not configured, use BS4)
    print("\n--- Testing live price scraper ---")
    price_data = scrape_live_price("HDFCBANK")
    if price_data:
        print(f"HDFCBANK: price={price_data.get('price')}, change={price_data.get('change')}")
    else:
        print("HDFCBANK: scrape returned None (market may be closed or rate limited)")

    print("\n" + "=" * 60)
    print("Self-test complete")
    print("=" * 60)
