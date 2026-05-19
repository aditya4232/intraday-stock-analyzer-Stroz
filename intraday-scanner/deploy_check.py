"""
deploy_check.py — Quick pre-deploy validator
Run: python deploy_check.py

Checks:
 - Python version
 - Presence of key packages (imports)
 - Presence of ScrapeGraphAI / LLM environment variables

This script does not send any secrets; it only checks existence.
"""

import sys
import importlib
import os

REQUIRED_PACKAGES = {
    "streamlit": "streamlit",
    "yfinance": "yfinance",
    "pandas": "pandas",
    "numpy": "numpy",
    "plotly": "plotly",
    "streamlit-autorefresh": "streamlit_autorefresh",
    "openpyxl": "openpyxl",
    "python-dotenv": "dotenv",
    "requests": "requests",
    "beautifulsoup4": "bs4",
    "scrapegraphai (optional)": "scrapegraphai",
}

ENV_VARS = [
    "SCRAPEGRAPHAI_CLOUD_API_KEY",
    "SCRAPE_LLM_API_KEY",
    "SCRAPE_LLM_PROVIDER",
    "SCRAPE_LLM_MODEL",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
]


def check_python_version():
    major, minor = sys.version_info[:2]
    print(f"Python version: {major}.{minor}")
    if major < 3 or (major == 3 and minor < 10):
        print("WARNING: Python 3.10+ is recommended.")


def check_packages():
    print("\nChecking packages:")
    missing = []
    for pretty, mod in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(mod)
            print(f"  OK: {pretty} -> import '{mod}' succeeded")
        except Exception:
            print(f"  MISSING: {pretty} -> import '{mod}' failed")
            missing.append(pretty)
    return missing


def check_env_vars():
    print("\nChecking environment variables (presence only):")
    present = {}
    for v in ENV_VARS:
        val = os.getenv(v)
        present[v] = bool(val)
        print(f"  {v}: {'SET' if val else 'NOT SET'}")
    # Additional check: detect SGAI key format
    sgai_key = os.getenv("SCRAPEGRAPHAI_CLOUD_API_KEY") or os.getenv("SCRAPE_LLM_API_KEY")
    if sgai_key and sgai_key.startswith("sgai-"):
        print("  Detected ScrapeGraphAI cloud key (sgai-...)")
    return present


if __name__ == '__main__':
    print("Deploy check for intraday-scanner")
    check_python_version()
    missing = check_packages()
    envs = check_env_vars()

    print("\nSummary:")
    if missing:
        print(f"  Packages missing: {len(missing)} (see list above)")
    else:
        print("  All required packages appear importable (optional SGAI may still be missing).")

    if not any(envs.values()):
        print("  No LLM / SGAI-related environment variables set — scraper will use fallbacks.")
    else:
        print("  Some environment variables are set. Ensure secrets are configured in your deployment platform.")

    print("\nNext steps: install missing packages (pip install -r requirements.txt) and set needed env vars before deploying to Streamlit.")
