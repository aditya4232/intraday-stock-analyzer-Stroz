"""
stocks_db.py — NSE Stock Universe by Sector
=============================================
Single source of truth for all NSE equity symbols organized by sector.
Only the most liquid, high-volume stocks for intraday trading.
Each symbol carries the .NS suffix required by yfinance.
"""

NSE_STOCKS: dict[str, list[str]] = {
    "All Sectors": [],
    "Banking": [
        "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS",
        "SBIN.NS", "INDUSINDBK.NS", "FEDERALBNK.NS", "RBLBANK.NS",
        "BANDHANBNK.NS", "IDFCFIRSTB.NS", "PNB.NS", "BANKBARODA.NS",
        "YESBANK.NS", "AUBANK.NS", "IDBI.NS",
    ],
    "IT": [
        "INFY.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS",
        "LTTS.NS", "COFORGE.NS", "MPHASIS.NS", "PERSISTENT.NS",
        "MINDTECK.NS", "OFSS.NS", "CYIENT.NS", "ZENSARTECH.NS",
    ],
    "Pharma": [
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
        "AUROPHARMA.NS", "BIOCON.NS", "LUPIN.NS", "ZYDUSLIFE.NS",
        "GLENMARK.NS", "TORNTPHARM.NS", "ALKEM.NS", "LAURUSLABS.NS",
        "APOLLOHOSP.NS", "GRANULES.NS",
    ],
    "Auto": [
        "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS",
        "EICHERMOT.NS", "HEROMOTOCO.NS", "ASHOKLEY.NS", "BALKRISIND.NS",
        "BOSCHLTD.NS", "TIINDIA.NS", "EXIDEIND.NS",
        "MRF.NS", "APOLLOTYRE.NS",
    ],
    "Finance": [
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCAMC.NS", "MUTHOOTFIN.NS",
        "CHOLAFIN.NS", "SRTRANSFIN.NS", "PEL.NS", "LICHSGFIN.NS",
        "HDFCLIFE.NS", "ICICIPRULI.NS", "SBILIFE.NS", "NYKAA.NS",
        "PAYTM.NS", "ZOMATO.NS",
    ],
    "FMCG": [
        "HINDUNILVR.NS", "ITC.NS", "BRITANNIA.NS", "NESTLEIND.NS",
        "MARICO.NS", "DABUR.NS", "GODREJCP.NS", "TATACONSUM.NS",
        "COLPAL.NS", "EMAMILTD.NS", "PIDILITIND.NS", "MCDOWELL-N.NS",
        "PGHH.NS", "VBL.NS",
    ],
    "Metals": [
        "TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "NATIONALUM.NS",
        "SAIL.NS", "HINDZINC.NS", "VEDL.NS", "JINDALSTEL.NS",
        "APLAPOLLO.NS", "RATNAMANI.NS", "WELCORP.NS",
    ],
    "Energy": [
        "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS",
        "ADANIGREEN.NS", "TATAPOWER.NS", "COALINDIA.NS", "BPCL.NS",
        "IOC.NS", "GAIL.NS", "ADANIPORTS.NS", "GUJGASLTD.NS",
        "IGL.NS", "TORNTPOWER.NS", "JSWENERGY.NS",
    ],
}

# Build the "All Sectors" list (deduplicated)
_all_symbols: list[str] = []
for sector, symbols in NSE_STOCKS.items():
    if sector == "All Sectors":
        continue
    for sym in symbols:
        if sym not in _all_symbols:
            _all_symbols.append(sym)
NSE_STOCKS["All Sectors"] = _all_symbols


def get_sectors() -> list[str]:
    """Return the list of available sector names (excluding 'All Sectors' as first option)."""
    return list(NSE_STOCKS.keys())


def get_symbols(sector: str) -> list[str]:
    """Return all stock symbols for a given sector."""
    return NSE_STOCKS.get(sector, [])


def get_symbol_count(sector: str) -> int:
    """Return the number of stocks in a sector."""
    return len(NSE_STOCKS.get(sector, []))


if __name__ == "__main__":
    print(f"Total sectors: {len(get_sectors())}")
    for sec in get_sectors():
        print(f"  {sec}: {get_symbol_count(sec)} stocks")
