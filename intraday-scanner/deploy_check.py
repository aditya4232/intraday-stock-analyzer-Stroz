"""
deploy_check.py — Quick pre-deploy validator
Run: python deploy_check.py

Checks:
 - Python version
 - Presence of key packages (imports)
"""

import sys
import importlib

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
}


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
            print(f"  OK: {pretty}")
        except Exception:
            print(f"  MISSING: {pretty}")
            missing.append(pretty)
    return missing


if __name__ == '__main__':
    print("Deploy check for intraday-scanner")
    check_python_version()
    missing = check_packages()

    print("\nSummary:")
    if missing:
        print(f"  Packages missing: {len(missing)} (see list above)")
    else:
        print("  All required packages appear importable.")
