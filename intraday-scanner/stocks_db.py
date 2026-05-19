"""
stocks_db.py — NSE Stock Universe by Sector (Nifty 50 + 300+ Extended Universe)
================================================================================

Single source of truth for all NSE equity symbols organized by sector.
Maintains the official Nifty 50 constituent list and extends to 300+ stocks
from the broader market for comprehensive scanning.

Features:
  - Nifty 50 constituent symbols (with membership badge)
  - Sector-wise categorization for every stock
  - Company names for display
  - Market cap classification (Large/Mid/Small cap)
  - Sectoral index mapping (Nifty Bank, Nifty IT, Nifty Pharma, etc.)
  - 300+ stocks covering all major sectors
  - Only liquid, high-volume stocks suitable for intraday trading
  - Each symbol carries the .NS suffix required by yfinance
"""

from typing import Optional

# =============================================================================
# Company Names (for display in the scanner UI)
# =============================================================================
COMPANY_NAMES: dict[str, str] = {
    # Banking
    "HDFCBANK": "HDFC Bank Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "SBIN": "State Bank of India",
    "INDUSINDBK": "IndusInd Bank Ltd",
    "FEDERALBNK": "Federal Bank Ltd",
    "RBLBANK": "RBL Bank Ltd",
    "BANDHANBNK": "Bandhan Bank Ltd",
    "IDFCFIRSTB": "IDFC First Bank Ltd",
    "PNB": "Punjab National Bank",
    "BANKBARODA": "Bank of Baroda",
    "YESBANK": "Yes Bank Ltd",
    "AUBANK": "AU Small Finance Bank",
    "IDBI": "IDBI Bank Ltd",
    "CANBK": "Canara Bank",
    "UNIONBANK": "Union Bank of India",
    "INDIANB": "Indian Bank",
    "UCOBANK": "UCO Bank",
    "BANKINDIA": "Bank of India",
    "CSBBANK": "CSB Bank Ltd",
    "KARURVYSYA": "Karur Vysya Bank",
    "SOUTHBANK": "South Indian Bank",
    "J&KBANK": "Jammu & Kashmir Bank",
    "DCBBANK": "DCB Bank Ltd",
    # Finance
    "BAJFINANCE": "Bajaj Finance Ltd",
    "BAJAJFINSV": "Bajaj Finserv Ltd",
    "HDFCAMC": "HDFC AMC Ltd",
    "MUTHOOTFIN": "Muthoot Finance Ltd",
    "CHOLAFIN": "Cholamandalam Investment",
    "SRTRANSFIN": "Shriram Transport Finance",
    "PEL": "Piramal Enterprises Ltd",
    "LICHSGFIN": "LIC Housing Finance Ltd",
    "HDFCLIFE": "HDFC Life Insurance",
    "ICICIPRULI": "ICICI Prudential Life",
    "SBILIFE": "SBI Life Insurance",
    "ICICIGI": "ICICI Lombard General Insurance",
    "STARHEALTH": "Star Health Insurance",
    "MAXHEALTH": "Max Healthcare Institute",
    "DMART": "Avenue Supermarts (DMart)",
    "SBICARD": "SBI Cards & Payment Services",
    "MANAPPURAM": "Manappuram Finance Ltd",
    "POONAWALLA": "Poonawalla Fincorp",
    "MASFIN": "MAS Financial Services",
    "CREDITACC": "CreditAccess Grameen",
    "IIFL": "IIFL Finance Ltd",
    "MONEYBOXX": "Moneymoneyboxx Finance",
    "NYKAA": "FSN E-Commerce (Nykaa)",
    "PAYTM": "One 97 Communications (Paytm)",
    "ZOMATO": "Zomato Ltd",
    # IT
    "INFY": "Infosys Ltd",
    "TCS": "Tata Consultancy Services",
    "WIPRO": "Wipro Ltd",
    "HCLTECH": "HCL Technologies Ltd",
    "TECHM": "Tech Mahindra Ltd",
    "LTTS": "L&T Technology Services",
    "COFORGE": "Coforge Ltd",
    "MPHASIS": "Mphasis Ltd",
    "PERSISTENT": "Persistent Systems Ltd",
    "MINDTECK": "Mindteck (India) Ltd",
    "OFSS": "Oracle Financial Services",
    "CYIENT": "Cyient Ltd",
    "ZENSARTECH": "Zensar Technologies",
    "LTIM": "LTIMindtree Ltd",
    "BIRLASOFT": "Birlasoft Ltd",
    "TATAELXSI": "Tata Elxsi Ltd",
    "HEXAWARE": "Hexaware Technologies",
    "KPITTECH": "KPIT Technologies Ltd",
    "MIDHANI": "Mishra Dhatu Nigam Ltd",
    "SONATSOFTW": "Sonata Software Ltd",
    "INFIBEAM": "Infibeam Avenues Ltd",
    "INTELLECT": "Intellect Design Arena",
    # Pharma
    "SUNPHARMA": "Sun Pharmaceutical Industries",
    "DRREDDY": "Dr. Reddy's Laboratories",
    "CIPLA": "Cipla Ltd",
    "DIVISLAB": "Divi's Laboratories Ltd",
    "APOLLOHOSP": "Apollo Hospitals Enterprise",
    "AUROPHARMA": "Aurobindo Pharma Ltd",
    "BIOCON": "Biocon Ltd",
    "LUPIN": "Lupin Ltd",
    "ZYDUSLIFE": "Zydus Lifesciences Ltd",
    "GLENMARK": "Glenmark Pharmaceuticals",
    "TORNTPHARM": "Torrent Pharmaceuticals Ltd",
    "ALKEM": "Alkem Laboratories Ltd",
    "LAURUSLABS": "Laurus Labs Ltd",
    "GRANULES": "Granules India Ltd",
    "CADILAHC": "Cadila Healthcare (Zydus)",
    "NATCOPHARM": "Natco Pharma Ltd",
    "IPCA": "Ipca Laboratories Ltd",
    "ABBOTINDIA": "Abbott India Ltd",
    "PFIZER": "Pfizer Ltd",
    "SANOFI": "Sanofi India Ltd",
    "GLAXO": "GlaxoSmithKline Pharmaceuticals",
    "MANKIND": "Mankind Pharma Ltd",
    "JBMA": "JBM Auto Ltd",
    # Auto
    "MARUTI": "Maruti Suzuki India Ltd",
    "TATAMOTORS": "Tata Motors Ltd",
    "M&M": "Mahindra & Mahindra Ltd",
    "BAJAJ-AUTO": "Bajaj Auto Ltd",
    "EICHERMOT": "Eicher Motors Ltd",
    "HEROMOTOCO": "Hero MotoCorp Ltd",
    "ASHOKLEY": "Ashok Leyland Ltd",
    "BALKRISIND": "Balkrishna Industries Ltd",
    "BOSCHLTD": "Bosch Ltd",
    "TIINDIA": "Tube Investments of India",
    "EXIDEIND": "Exide Industries Ltd",
    "MRF": "MRF Ltd",
    "APOLLOTYRE": "Apollo Tyres Ltd",
    "TVSMOTOR": "TVS Motor Company Ltd",
    "MOTHERSUMI": "Motherson Sumi Wiring India",
    "SAMIL": "Samvardhana Motherson International",
    "ENDURANCE": "Endurance Technologies Ltd",
    "SUNDARMFIN": "Sundaram Finance Ltd",
    "SONACOMS": "Sona BLW Precision Forgings",
    "LUMINDS": "Lumax Industries Ltd",
    # FMCG
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "ITC": "ITC Ltd",
    "BRITANNIA": "Britannia Industries Ltd",
    "NESTLEIND": "Nestle India Ltd",
    "MARICO": "Marico Ltd",
    "DABUR": "Dabur India Ltd",
    "GODREJCP": "Godrej Consumer Products",
    "TATACONSUM": "Tata Consumer Products Ltd",
    "COLPAL": "Colgate-Palmolive India",
    "EMAMILTD": "Emami Ltd",
    "PIDILITIND": "Pidilite Industries Ltd",
    "MCDOWELL-N": "United Spirits Ltd",
    "PGHH": "Procter & Gamble Hygiene",
    "VBL": "Varun Beverages Ltd",
    "RADICO": "Radico Khaitan Ltd",
    "GODREJAGRO": "Godrej Agrovet Ltd",
    "KRBL": "KRBL Ltd",
    "BATAINDIA": "Bata India Ltd",
    "METROBRAND": "Metro Brands Ltd",
    # Metals & Mining
    "TATASTEEL": "Tata Steel Ltd",
    "HINDALCO": "Hindalco Industries Ltd",
    "JSWSTEEL": "JSW Steel Ltd",
    "NATIONALUM": "National Aluminium Co Ltd",
    "SAIL": "Steel Authority of India Ltd",
    "HINDZINC": "Hindustan Zinc Ltd",
    "VEDL": "Vedanta Ltd",
    "JINDALSTEL": "Jindal Steel & Power Ltd",
    "APLAPOLLO": "APL Apollo Tubes Ltd",
    "RATNAMANI": "Ratnamani Metals & Tubes",
    "WELCORP": "Welspun Corp Ltd",
    "MOIL": "MOIL Ltd",
    "NMDC": "NMDC Ltd",
    "KIOCL": "KIOCL Ltd",
    # Energy
    "RELIANCE": "Reliance Industries Ltd",
    "ONGC": "Oil & Natural Gas Corp Ltd",
    "NTPC": "NTPC Ltd",
    "POWERGRID": "Power Grid Corp of India",
    "ADANIGREEN": "Adani Green Energy Ltd",
    "TATAPOWER": "Tata Power Company Ltd",
    "COALINDIA": "Coal India Ltd",
    "BPCL": "Bharat Petroleum Corp Ltd",
    "IOC": "Indian Oil Corp Ltd",
    "GAIL": "GAIL (India) Ltd",
    "ADANIPORTS": "Adani Ports & SEZ Ltd",
    "GUJGASLTD": "Gujarat Gas Ltd",
    "IGL": "Indraprastha Gas Ltd",
    "TORNTPOWER": "Torrent Power Ltd",
    "JSWENERGY": "JSW Energy Ltd",
    "NHPC": "NHPC Ltd",
    "SJVN": "SJVN Ltd",
    "CESC": "CESC Ltd",
    "ADANIENSOL": "Adani Energy Solutions",
    # Telecom
    "BHARTIARTL": "Bharti Airtel Ltd",
    "IDEA": "Vodafone Idea Ltd",
    "MTNL": "Mahanagar Telephone Nigam",
    "TATACOMM": "Tata Communications Ltd",
    "RAILTEL": "RailTel Corp of India",
    "TEJASNET": "Tejas Networks Ltd",
    # Cement
    "ULTRACEMCO": "UltraTech Cement Ltd",
    "GRASIM": "Grasim Industries Ltd",
    "AMBUJACEM": "Ambuja Cements Ltd",
    "ACC": "ACC Ltd",
    "RAMCOCEM": "Ramco Cements Ltd",
    "BIRLACORPN": "Birla Corp Ltd",
    "HEIDELBERG": "HeidelbergCement India",
    "JKLAKSHMI": "JK Lakshmi Cement Ltd",
    "SHREECEM": "Shree Cement Ltd",
    "DALMIASUG": "Dalmia Bharat Ltd",
    # Construction & Engineering
    "LT": "Larsen & Toubro Ltd",
    "L&TFH": "L&T Finance Holdings",
    "KNR": "KNR Constructions Ltd",
    "NAGAROIL": "Nagarnaik Oil & Gas",
    "PNCIL": "PNC Infratech Ltd",
    "GMRINFRA": "GMR Infrastructure Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "IRCON": "Ircon International Ltd",
    "NCC": "NCC Ltd",
    # Consumer Durables
    "TITAN": "Titan Company Ltd",
    "ASIANPAINT": "Asian Paints Ltd",
    "BERGER": "Berger Paints India Ltd",
    "KAJARIACER": "Kajaria Ceramics Ltd",
    "CROMPTON": "Crompton Greaves Consumer",
    "VOLTAS": "Voltas Ltd",
    "HAVELLS": "Havells India Ltd",
    "BLUESTAR": "Blue Star Ltd",
    "ORIENTELEC": "Orient Electric Ltd",
    "AMBER": "Amber Enterprises India",
    "VGUARD": "V-Guard Industries Ltd",
    "BAJAJELEC": "Bajaj Electricals Ltd",
    "BPL": "BPL Ltd",
    "BUTTERFLY": "Butterfly Gandhimathi Appliances",
    "PREMIER": "Premier Ltd",
    # Media
    "ZEEL": "Zee Entertainment Enterprises",
    "PVRINOX": "PVR Inox Ltd",
    "TV18BRDCST": "TV18 Broadcast Ltd",
    "NETWORK18": "Network18 Media & Investments",
    "SUNTV": "Sun TV Network Ltd",
    "JAGRAN": "Jagran Prakashan Ltd",
    "DBL": "Dilip Buildcon Ltd",
    "NAZARA": "Nazara Technologies Ltd",
    # Real Estate
    "DLF": "DLF Ltd",
    "GODREJPROP": "Godrej Properties Ltd",
    "OBEROIRLTY": "Oberoi Realty Ltd",
    "PHOENIXLTD": "Phoenix Mills Ltd",
    "BRIGADE": "Brigade Enterprises Ltd",
    "PRESTIGE": "Prestige Estates Projects",
    "SOBHA": "Sobha Ltd",
    "SUNTECK": "Sunteck Realty Ltd",
    "LODHA": "Macrotech Developers (Lodha)",
    # Textiles
    "PAGEIND": "Page Industries Ltd",
    "TRENT": "Trent Ltd",
    "ABFRL": "Aditya Birla Fashion & Retail",
    "ADITYABIRLA": "Aditya Birla Group",
    "RAYMOND": "Raymond Ltd",
    "VXM": "VXL Instruments",
    "ALOKINDS": "Alok Industries Ltd",
    "WELSPUN": "Welspun Living Ltd",
    # Chemicals
    "DEEPAKNTR": "Deepak Nitrite Ltd",
    "SRF": "SRF Ltd",
    "GODREJIND": "Godrej Industries Ltd",
    "LINDE": "Linde India Ltd",
    "GUJALKALI": "Gujarat Alkalies & Chemicals",
    "FLUOROCHEM": "Gujarat Fluorochemicals",
    "AARTIIND": "Aarti Industries Ltd",
    "VINATIORGA": "Vinati Organics Ltd",
    "NAVINFLUOR": "Navin Fluorine International",
    # Logistics
    "DELHIVERY": "Delhivery Ltd",
    "TCIEXP": "TCI Express Ltd",
    "GATI": "Gati Ltd",
    "MAHLOG": "Mahindra Logistics Ltd",
    "CONCOR": "Container Corp of India",
    "BLUEDART": "Blue Dart Express Ltd",
    "SAFARI": "Safari Industries (India)",
    "VRLLOG": "VRL Logistics Ltd",
    # Agriculture
    "COROMANDEL": "Coromandel International",
    "UPL": "UPL Ltd",
    "PIIND": "PI Industries Ltd",
    "BAYERCROP": "Bayer CropScience Ltd",
    "RALLIS": "Rallis India Ltd",
    "GNFC": "Gujarat Narmada Valley Fertilizers",
    "CHAMBLFERT": "Chambal Fertilizers & Chemicals",
    "NACLIND": "NACL Industries Ltd",
    "DEEPAKFERT": "Deepak Fertilizers",
    # Hospitality
    "INDHOTEL": "Indian Hotels Company Ltd",
    "LEMONTREE": "Lemon Tree Hotels Ltd",
    "EIHOTEL": "EIH Ltd (Oberoi Hotels)",
    "JUBLFOOD": "Jubilant FoodWorks Ltd",
    "RESTAURANT": "Restaurant Brands Asia",
    "WESTLIFE": "Westlife Foodworld Ltd",
    # Power & Infra
    "ADANITRANS": "Adani Transmission Ltd",
    "SIEMENS": "Siemens Ltd",
    "ABB": "ABB India Ltd",
    "BHEL": "Bharat Heavy Electricals Ltd",
    "THERMAX": "Thermax Ltd",
    "KEC": "KEC International Ltd",
    "KALPATPOWR": "Kalpataru Power Transmission",
    "CGCL": "Crompton Greaves (CG Power)",
    "POWERMECH": "Power Mech Projects Ltd",
}

# Normalize
COMPANY_NAMES = {k.upper(): v for k, v in COMPANY_NAMES.items()}


# =============================================================================
# Market Cap Classification
# =============================================================================
MARKET_CAP: dict[str, str] = {
    # Large Cap (>50,000 Cr) — Nifty 50 + major blue chips
    "RELIANCE": "Large Cap", "TCS": "Large Cap", "HDFCBANK": "Large Cap",
    "INFY": "Large Cap", "ICICIBANK": "Large Cap", "BHARTIARTL": "Large Cap",
    "SBIN": "Large Cap", "BAJFINANCE": "Large Cap", "HINDUNILVR": "Large Cap",
    "ITC": "Large Cap", "KOTAKBANK": "Large Cap", "AXISBANK": "Large Cap",
    "LT": "Large Cap", "DMART": "Large Cap", "ASIANPAINT": "Large Cap",
    "MARUTI": "Large Cap", "TITAN": "Large Cap", "SUNPHARMA": "Large Cap",
    "NTPC": "Large Cap", "ONGC": "Large Cap", "POWERGRID": "Large Cap",
    "ULTRACEMCO": "Large Cap", "HCLTECH": "Large Cap", "WIPRO": "Large Cap",
    "ADANIENT": "Large Cap", "ADANIPORTS": "Large Cap", "ADANIGREEN": "Large Cap",
    "BAJAJFINSV": "Large Cap", "HDFCLIFE": "Large Cap", "SBILIFE": "Large Cap",
    "TATASTEEL": "Large Cap", "JSWSTEEL": "Large Cap", "TATAMOTORS": "Large Cap",
    "M&M": "Large Cap", "NESTLEIND": "Large Cap", "BRITANNIA": "Large Cap",
    "DRREDDY": "Large Cap", "CIPLA": "Large Cap", "APOLLOHOSP": "Large Cap",
    "BAJAJ-AUTO": "Large Cap", "EICHERMOT": "Large Cap", "HEROMOTOCO": "Large Cap",
    "COALINDIA": "Large Cap", "BPCL": "Large Cap", "IOC": "Large Cap",
    "GAIL": "Large Cap", "GRASIM": "Large Cap", "HINDALCO": "Large Cap",
    "DIVISLAB": "Large Cap", "TECHM": "Large Cap", "TATACONSUM": "Large Cap",
    "PIDILITIND": "Large Cap", "VEDL": "Large Cap", "ZOMATO": "Large Cap",
    "LTIM": "Large Cap", "TRENT": "Large Cap",
    # Mid Cap (10,000 - 50,000 Cr)
    "INDUSINDBK": "Mid Cap", "BANDHANBNK": "Mid Cap", "PNB": "Mid Cap",
    "FEDERALBNK": "Mid Cap", "BANKBARODA": "Mid Cap", "IDFCFIRSTB": "Mid Cap",
    "YESBANK": "Mid Cap", "AUBANK": "Mid Cap", "CANBK": "Mid Cap",
    "PERSISTENT": "Mid Cap", "LTTS": "Mid Cap", "COFORGE": "Mid Cap",
    "MPHASIS": "Mid Cap", "ZENSARTECH": "Mid Cap", "HEXAWARE": "Mid Cap",
    "KPITTECH": "Mid Cap", "CYIENT": "Mid Cap", "SONATSOFTW": "Mid Cap",
    "MUTHOOTFIN": "Mid Cap", "CHOLAFIN": "Mid Cap", "SRTRANSFIN": "Mid Cap",
    "LICHSGFIN": "Mid Cap", "ICICIPRULI": "Mid Cap", "ICICIGI": "Mid Cap",
    "MAXHEALTH": "Mid Cap", "SBICARD": "Mid Cap", "NYKAA": "Mid Cap",
    "PAYTM": "Mid Cap", "TVSMOTOR": "Mid Cap", "MRF": "Mid Cap",
    "ASHOKLEY": "Mid Cap", "BOSCHLTD": "Mid Cap", "BALKRISIND": "Mid Cap",
    "MOTHERSUMI": "Mid Cap", "SONACOMS": "Mid Cap", "EXIDEIND": "Mid Cap",
    "DABUR": "Mid Cap", "GODREJCP": "Mid Cap", "MARICO": "Mid Cap",
    "COLPAL": "Mid Cap", "VBL": "Mid Cap", "PGHH": "Mid Cap",
    "MCDOWELL-N": "Mid Cap", "BERGER": "Mid Cap", "HAVELLS": "Mid Cap",
    "CROMPTON": "Mid Cap", "VOLTAS": "Mid Cap", "KAJARIACER": "Mid Cap",
    "AUROPHARMA": "Mid Cap", "BIOCON": "Mid Cap", "LUPIN": "Mid Cap",
    "ZYDUSLIFE": "Mid Cap", "TORNTPHARM": "Mid Cap", "ALKEM": "Mid Cap",
    "LAURUSLABS": "Mid Cap", "MANKIND": "Mid Cap", "GLENMARK": "Mid Cap",
    "JINDALSTEL": "Mid Cap", "SAIL": "Mid Cap", "NATIONALUM": "Mid Cap",
    "APLAPOLLO": "Mid Cap", "NMDC": "Mid Cap", "HINDZINC": "Mid Cap",
    "GODREJPROP": "Mid Cap", "DLF": "Mid Cap", "OBEROIRLTY": "Mid Cap",
    "PHOENIXLTD": "Mid Cap", "PRESTIGE": "Mid Cap", "LODHA": "Mid Cap",
    "ADANITRANS": "Mid Cap", "SIEMENS": "Mid Cap", "ABB": "Mid Cap",
    "BHEL": "Mid Cap", "THERMAX": "Mid Cap", "GMRINFRA": "Mid Cap",
    "NHPC": "Mid Cap", "SJVN": "Mid Cap", "JSWENERGY": "Mid Cap",
    "TATAPOWER": "Mid Cap", "TORNTPOWER": "Mid Cap", "CESC": "Mid Cap",
    "IGL": "Mid Cap", "GUJGASLTD": "Mid Cap", "MCDOWELL-N": "Mid Cap",
    "AMBUJACEM": "Mid Cap", "ACC": "Mid Cap", "RAMCOCEM": "Mid Cap",
    "SHREECEM": "Mid Cap", "DALMIASUG": "Mid Cap", "BIRLACORPN": "Mid Cap",
    "L&TFH": "Mid Cap", "NCC": "Mid Cap", "IRCON": "Mid Cap",
    "PAGEIND": "Mid Cap", "ABFRL": "Mid Cap", "RAYMOND": "Mid Cap",
    "SRF": "Mid Cap", "DEEPAKNTR": "Mid Cap", "AARTIIND": "Mid Cap",
    "FLUOROCHEM": "Mid Cap", "NAVINFLUOR": "Mid Cap", "VINATIORGA": "Mid Cap",
    "UPL": "Mid Cap", "PIIND": "Mid Cap", "COROMANDEL": "Mid Cap",
    "CONCOR": "Mid Cap", "BLUEDART": "Mid Cap", "DELHIVERY": "Mid Cap",
    "INDHOTEL": "Mid Cap", "JUBLFOOD": "Mid Cap", "PVRINOX": "Mid Cap",
    "ZEEL": "Mid Cap", "SUNTV": "Mid Cap",
    "POONAWALLA": "Mid Cap", "MANAPPURAM": "Mid Cap", "CREDITACC": "Mid Cap",
    "IIFL": "Mid Cap", "TATAELXSI": "Mid Cap", "OFSS": "Mid Cap",
    "BIRLASOFT": "Mid Cap", "INTELLECT": "Mid Cap", "INFIBEAM": "Mid Cap",
    "WELCORP": "Mid Cap", "RATNAMANI": "Mid Cap", "MOIL": "Mid Cap",
    "ADANIENSOL": "Mid Cap", "TATACOMM": "Mid Cap",
    # Small Cap (<10,000 Cr) — rest default to Small Cap
}

# Default: any stock not in MARKET_CAP is Small Cap


# =============================================================================
# Sectoral Indices (Nifty sector indices)
# =============================================================================
SECTORAL_INDICES: dict[str, str] = {
    # Nifty Bank
    "HDFCBANK": "Nifty Bank", "ICICIBANK": "Nifty Bank", "AXISBANK": "Nifty Bank",
    "KOTAKBANK": "Nifty Bank", "SBIN": "Nifty Bank", "INDUSINDBK": "Nifty Bank",
    "FEDERALBNK": "Nifty Bank", "RBLBANK": "Nifty Bank", "BANDHANBNK": "Nifty Bank",
    "IDFCFIRSTB": "Nifty Bank", "PNB": "Nifty Bank", "BANKBARODA": "Nifty Bank",
    "YESBANK": "Nifty Bank", "AUBANK": "Nifty Bank", "IDBI": "Nifty Bank",
    "CANBK": "Nifty Bank",
    # Nifty IT
    "INFY": "Nifty IT", "TCS": "Nifty IT", "WIPRO": "Nifty IT",
    "HCLTECH": "Nifty IT", "TECHM": "Nifty IT", "LTTS": "Nifty IT",
    "COFORGE": "Nifty IT", "MPHASIS": "Nifty IT", "PERSISTENT": "Nifty IT",
    "LTIM": "Nifty IT", "TATAELXSI": "Nifty IT",
    # Nifty Pharma
    "SUNPHARMA": "Nifty Pharma", "DRREDDY": "Nifty Pharma", "CIPLA": "Nifty Pharma",
    "DIVISLAB": "Nifty Pharma", "APOLLOHOSP": "Nifty Pharma",
    "AUROPHARMA": "Nifty Pharma", "BIOCON": "Nifty Pharma", "LUPIN": "Nifty Pharma",
    "ZYDUSLIFE": "Nifty Pharma", "TORNTPHARM": "Nifty Pharma",
    "ALKEM": "Nifty Pharma", "LAURUSLABS": "Nifty Pharma",
    # Nifty Auto
    "MARUTI": "Nifty Auto", "TATAMOTORS": "Nifty Auto", "M&M": "Nifty Auto",
    "BAJAJ-AUTO": "Nifty Auto", "EICHERMOT": "Nifty Auto", "HEROMOTOCO": "Nifty Auto",
    "TVSMOTOR": "Nifty Auto", "ASHOKLEY": "Nifty Auto", "BALKRISIND": "Nifty Auto",
    "BOSCHLTD": "Nifty Auto", "MRF": "Nifty Auto", "APOLLOTYRE": "Nifty Auto",
    "EXIDEIND": "Nifty Auto", "MOTHERSUMI": "Nifty Auto",
    # Nifty FMCG
    "HINDUNILVR": "Nifty FMCG", "ITC": "Nifty FMCG", "BRITANNIA": "Nifty FMCG",
    "NESTLEIND": "Nifty FMCG", "MARICO": "Nifty FMCG", "DABUR": "Nifty FMCG",
    "GODREJCP": "Nifty FMCG", "TATACONSUM": "Nifty FMCG", "COLPAL": "Nifty FMCG",
    "PIDILITIND": "Nifty FMCG",
    # Nifty Metal
    "TATASTEEL": "Nifty Metal", "HINDALCO": "Nifty Metal", "JSWSTEEL": "Nifty Metal",
    "NATIONALUM": "Nifty Metal", "SAIL": "Nifty Metal", "HINDZINC": "Nifty Metal",
    "VEDL": "Nifty Metal", "JINDALSTEL": "Nifty Metal", "NMDC": "Nifty Metal",
    "APLAPOLLO": "Nifty Metal", "RATNAMANI": "Nifty Metal", "WELCORP": "Nifty Metal",
    # Nifty Energy
    "RELIANCE": "Nifty Energy", "ONGC": "Nifty Energy", "NTPC": "Nifty Energy",
    "POWERGRID": "Nifty Energy", "COALINDIA": "Nifty Energy", "BPCL": "Nifty Energy",
    "IOC": "Nifty Energy", "GAIL": "Nifty Energy", "ADANIPORTS": "Nifty Energy",
    "TATAPOWER": "Nifty Energy", "ADANIGREEN": "Nifty Energy",
    # Nifty Realty
    "DLF": "Nifty Realty", "GODREJPROP": "Nifty Realty", "OBEROIRLTY": "Nifty Realty",
    "PHOENIXLTD": "Nifty Realty", "BRIGADE": "Nifty Realty", "PRESTIGE": "Nifty Realty",
    "SOBHA": "Nifty Realty", "SUNTECK": "Nifty Realty", "LODHA": "Nifty Realty",
    # Nifty Media
    "ZEEL": "Nifty Media", "PVRINOX": "Nifty Media", "TV18BRDCST": "Nifty Media",
    "NETWORK18": "Nifty Media", "SUNTV": "Nifty Media",
    # Nifty Consumer Durables
    "TITAN": "Nifty Consumer Durables", "ASIANPAINT": "Nifty Consumer Durables",
    "HAVELLS": "Nifty Consumer Durables", "VOLTAS": "Nifty Consumer Durables",
    "CROMPTON": "Nifty Consumer Durables", "BLUESTAR": "Nifty Consumer Durables",
    "KAJARIACER": "Nifty Consumer Durables", "BERGER": "Nifty Consumer Durables",
}


# =============================================================================
# Nifty 50 Constituents (Official list)
# =============================================================================
NIFTY50_SYMBOLS: set[str] = {
    # Financial Services (10)
    "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN",
    "INDUSINDBK", "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE",
    # IT (5)
    "INFY", "TCS", "WIPRO", "HCLTECH", "TECHM",
    # Energy (6)
    "RELIANCE", "ONGC", "NTPC", "POWERGRID", "BPCL", "COALINDIA",
    # Auto (5)
    "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT",
    # FMCG (5)
    "HINDUNILVR", "ITC", "BRITANNIA", "NESTLEIND", "TATACONSUM",
    # Pharma (4)
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB",
    # Metals & Mining (3)
    "TATASTEEL", "HINDALCO", "JSWSTEEL",
    # Telecom (1)
    "BHARTIARTL",
    # Cement & Construction (4)
    "ULTRACEMCO", "GRASIM", "LT", "ADANIPORTS",
    # Consumer Durables (2)
    "TITAN", "ASIANPAINT",
    # Media (1)
    "ZEEL",
    # Others (4)
    "ADANIENT", "APOLLOHOSP", "HEROMOTOCO", "PIDILITIND",
}

# Normalize
NIFTY50_SYMBOLS = {sym.upper() for sym in NIFTY50_SYMBOLS}


# =============================================================================
# Stock -> Sector Mapping (single source of truth)
# =============================================================================
_STOCK_SECTORS_RAW: dict[str, str] = {
    # ---- Financial Services / Banking ----
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "SBIN": "Banking", "INDUSINDBK": "Banking",
    "FEDERALBNK": "Banking", "RBLBANK": "Banking", "BANDHANBNK": "Banking",
    "IDFCFIRSTB": "Banking", "PNB": "Banking", "BANKBARODA": "Banking",
    "YESBANK": "Banking", "AUBANK": "Banking", "IDBI": "Banking",
    "CANBK": "Banking", "UNIONBANK": "Banking", "INDIANB": "Banking",
    "UCOBANK": "Banking", "BANKINDIA": "Banking", "CSBBANK": "Banking",
    "KARURVYSYA": "Banking", "SOUTHBANK": "Banking", "J&KBANK": "Banking",
    "DCBBANK": "Banking",     "EQUITASBNK": "Banking", "CUB": "Banking", "PSB": "Banking",

    # ---- Financial Services (NBFCs, Insurance, Fintech) ----
    "BAJFINANCE": "Finance", "BAJAJFINSV": "Finance", "HDFCAMC": "Finance",
    "MUTHOOTFIN": "Finance", "CHOLAFIN": "Finance", "SRTRANSFIN": "Finance",
    "PEL": "Finance", "LICHSGFIN": "Finance", "HDFCLIFE": "Finance",
    "ICICIPRULI": "Finance", "SBILIFE": "Finance", "ICICIGI": "Finance",
    "STARHEALTH": "Finance", "DMART": "Finance", "SBICARD": "Finance",
    "MANAPPURAM": "Finance", "POONAWALLA": "Finance", "MASFIN": "Finance",
    "CREDITACC": "Finance", "IIFL": "Finance", "NYKAA": "Finance",
    "PAYTM": "Finance",     "ZOMATO": "Finance", "POLICYBZR": "Finance", "CARTRADE": "Finance",

    # ---- Information Technology ----
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "HCLTECH": "IT",
    "TECHM": "IT", "LTTS": "IT", "COFORGE": "IT", "MPHASIS": "IT",
    "PERSISTENT": "IT", "OFSS": "IT", "CYIENT": "IT", "ZENSARTECH": "IT",
    "LTIM": "IT", "BIRLASOFT": "IT", "TATAELXSI": "IT", "HEXAWARE": "IT",
    "KPITTECH": "IT", "SONATSOFTW": "IT",     "INFIBEAM": "IT", "INTELLECT": "IT",
    "MINDTECK": "IT", "NIITTECH": "IT", "DATAPATNS": "IT",
    "NEWGEN": "IT", "HAPPSTMNDS": "IT", "TANLA": "IT",

    # ---- Pharmaceuticals & Healthcare ----
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
    "DIVISLAB": "Pharma", "APOLLOHOSP": "Pharma", "AUROPHARMA": "Pharma",
    "BIOCON": "Pharma", "LUPIN": "Pharma", "ZYDUSLIFE": "Pharma",
    "GLENMARK": "Pharma", "TORNTPHARM": "Pharma", "ALKEM": "Pharma",
    "LAURUSLABS": "Pharma", "GRANULES": "Pharma", "CADILAHC": "Pharma",
    "NATCOPHARM": "Pharma", "IPCA": "Pharma", "ABBOTINDIA": "Pharma",
    "PFIZER": "Pharma", "SANOFI": "Pharma", "GLAXO": "Pharma",
    "MANKIND": "Pharma",
    "JBMA": "Pharma", "NEULAND": "Pharma", "AJANTPHARM": "Pharma",
    "SYNGENE": "Pharma", "SUPRAJIT": "Pharma",

    # ---- Automobile & Auto Ancillaries ----
    "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto",
    "BAJAJ-AUTO": "Auto", "EICHERMOT": "Auto", "HEROMOTOCO": "Auto",
    "ASHOKLEY": "Auto", "BALKRISIND": "Auto", "BOSCHLTD": "Auto",
    "TIINDIA": "Auto", "EXIDEIND": "Auto", "MRF": "Auto",
    "APOLLOTYRE": "Auto", "TVSMOTOR": "Auto", "MOTHERSUMI": "Auto",
    "ENDURANCE": "Auto", "SUNDARMFIN": "Auto", "SONACOMS": "Auto",
    "LUMINDS": "Auto", "SAMIL": "Auto", "SETCO": "Auto",
    "JKTYRE": "Auto", "CEATLTD": "Auto",     "TVSSRICHAK": "Auto", "AUTOBE": "Auto", "UNOMINDA": "Auto",

    # ---- Fast-Moving Consumer Goods (FMCG) ----
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG", "MARICO": "FMCG", "DABUR": "FMCG",
    "GODREJCP": "FMCG", "TATACONSUM": "FMCG", "COLPAL": "FMCG",
    "EMAMILTD": "FMCG", "MCDOWELL-N": "FMCG", "PGHH": "FMCG",
    "VBL": "FMCG", "RADICO": "FMCG", "GODREJAGRO": "FMCG",
    "KRBL": "FMCG", "BATAINDIA": "FMCG", "METROBRAND": "FMCG",

    # ---- Consumer (PIDILITIND and others) ----
    "PIDILITIND": "Consumer",

    # ---- Metals & Mining ----
    "TATASTEEL": "Metals", "HINDALCO": "Metals", "JSWSTEEL": "Metals",
    "NATIONALUM": "Metals", "SAIL": "Metals", "HINDZINC": "Metals",
    "VEDL": "Metals", "JINDALSTEL": "Metals", "APLAPOLLO": "Metals",
    "RATNAMANI": "Metals", "WELCORP": "Metals", "MOIL": "Metals",
    "NMDC": "Metals", "KIOCL": "Metals",

    # ---- Energy (Oil & Gas, Power) ----
    "RELIANCE": "Energy", "ONGC": "Energy", "NTPC": "Energy",
    "POWERGRID": "Energy", "TATAPOWER": "Energy", "COALINDIA": "Energy",
    "BPCL": "Energy", "IOC": "Energy", "GAIL": "Energy",
    "ADANIGREEN": "Energy", "ADANIPORTS": "Energy", "GUJGASLTD": "Energy",
    "IGL": "Energy", "TORNTPOWER": "Energy", "JSWENERGY": "Energy",
    "NHPC": "Energy", "SJVN": "Energy", "CESC": "Energy",
    "ADANIENSOL": "Energy", "OIL": "Energy", "MRPL": "Energy",
    "HINDPETRO": "Energy", "CHENNPETRO": "Energy",

    # ---- Telecommunication ----
    "BHARTIARTL": "Telecom", "IDEA": "Telecom", "MTNL": "Telecom",
    "TATACOMM": "Telecom", "RAILTEL": "Telecom", "TEJASNET": "Telecom",

    # ---- Cement & Construction Materials ----
    "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement",
    "ACC": "Cement", "RAMCOCEM": "Cement", "BIRLACORPN": "Cement",
    "HEIDELBERG": "Cement", "JKLAKSHMI": "Cement", "SHREECEM": "Cement",
    "DALMIASUG": "Cement",

    # ---- Construction & Engineering ----
    "LT": "Construction", "ADANIENT": "Construction", "L&TFH": "Construction",
    "GMRINFRA": "Construction", "IRCON": "Construction", "NCC": "Construction",
    "PNCIL": "Construction", "KNR": "Construction", "HGINFRA": "Construction",

    # ---- Consumer Durables ----
    "TITAN": "Consumer Durables", "ASIANPAINT": "Consumer Durables",
    "BERGER": "Consumer Durables", "KAJARIACER": "Consumer Durables",
    "CROMPTON": "Consumer Durables", "VOLTAS": "Consumer Durables",
    "HAVELLS": "Consumer Durables", "BLUESTAR": "Consumer Durables",
    "ORIENTELEC": "Consumer Durables", "AMBER": "Consumer Durables",
    "VGUARD": "Consumer Durables", "BAJAJELEC": "Consumer Durables",

    # ---- Media & Entertainment ----
    "ZEEL": "Media", "PVRINOX": "Media", "TV18BRDCST": "Media",
    "NETWORK18": "Media", "SUNTV": "Media", "JAGRAN": "Media",
    "NAZARA": "Media",

    # ---- Real Estate ----
    "DLF": "Real Estate", "GODREJPROP": "Real Estate", "OBEROIRLTY": "Real Estate",
    "PHOENIXLTD": "Real Estate", "BRIGADE": "Real Estate", "PRESTIGE": "Real Estate",
    "SOBHA": "Real Estate", "SUNTECK": "Real Estate", "LODHA": "Real Estate",

    # ---- Textiles & Apparel ----
    "PAGEIND": "Textiles", "TRENT": "Textiles", "ABFRL": "Textiles",
    "RAYMOND": "Textiles", "ALOKINDS": "Textiles",     "WELSPUN": "Textiles", "VXLINSTR": "Textiles", "SPLPETRO": "Textiles",

    # ---- Chemicals ----
    "DEEPAKNTR": "Chemicals", "SRF": "Chemicals",
    "GODREJIND": "Chemicals", "LINDE": "Chemicals", "GUJALKALI": "Chemicals",
    "FLUOROCHEM": "Chemicals", "AARTIIND": "Chemicals", "VINATIORGA": "Chemicals",
    "NAVINFLUOR": "Chemicals", "CLEAN": "Chemicals", "FINEORG": "Chemicals",
    "ALKYLAMINE": "Chemicals", "BALAMINES": "Chemicals",

    # ---- Logistics ----
    "DELHIVERY": "Logistics", "TCIEXP": "Logistics", "GATI": "Logistics",
    "MAHLOG": "Logistics", "CONCOR": "Logistics", "BLUEDART": "Logistics",
    "VRLLOG": "Logistics",

    # ---- Agriculture & Fertilizers ----
    "COROMANDEL": "Agriculture", "UPL": "Agriculture", "PIIND": "Agriculture",
    "BAYERCROP": "Agriculture", "RALLIS": "Agriculture", "GNFC": "Agriculture",
    "CHAMBLFERT": "Agriculture",     "DEEPAKFERT": "Agriculture", "SHARDA": "Agriculture",
    "GHCL": "Agriculture", "RALLIS": "Agriculture", "INSECTICID": "Agriculture",

    # ---- Hospitality ----
    "INDHOTEL": "Hospitality", "LEMONTREE": "Hospitality", "EIHOTEL": "Hospitality",
    "JUBLFOOD": "Hospitality",     "WESTLIFE": "Hospitality", "RESTAURANT": "Hospitality",
    "SPECIALITY": "Hospitality", "BARBEQUE": "Hospitality",

    # ---- Power & Infrastructure ----
    "ADANITRANS": "Power & Infra", "SIEMENS": "Power & Infra",
    "ABB": "Power & Infra", "BHEL": "Power & Infra", "THERMAX": "Power & Infra",
    "KEC": "Power & Infra", "KALPATPOWR": "Power & Infra",
    "CGCL": "Power & Infra",     "POWERMECH": "Power & Infra", "TECHNOE": "Power & Infra",
    "JSWINFRA": "Power & Infra", "RPOWER": "Power & Infra",
}

# Normalize
STOCK_SECTORS: dict[str, str] = {k.upper(): v for k, v in _STOCK_SECTORS_RAW.items()}

# Remove the raw dict to prevent accidental use
del _STOCK_SECTORS_RAW


# =============================================================================
# Sector -> Stocks Mapping (for scanning)
# =============================================================================
_sector_groups: dict[str, list[str]] = {}
for symbol, sector in STOCK_SECTORS.items():
    if sector not in _sector_groups:
        _sector_groups[sector] = []
    _sector_groups[sector].append(f"{symbol}.NS")

for sector in _sector_groups:
    _sector_groups[sector].sort()

NSE_STOCKS: dict[str, list[str]] = {
    "All Sectors": [],
    **_sector_groups,
}

# Build "All Sectors" list (deduplicated)
_all_symbols: list[str] = []
for sector, symbols in _sector_groups.items():
    for sym in symbols:
        if sym not in _all_symbols:
            _all_symbols.append(sym)
NSE_STOCKS["All Sectors"] = _all_symbols


# =============================================================================
# Nifty 50 sector breakdown (helper for display)
# =============================================================================
NIFTY50_SECTORS: dict[str, list[str]] = {}
for sym_raw in NIFTY50_SYMBOLS:
    sec = STOCK_SECTORS.get(sym_raw, "Unknown")
    if sec not in NIFTY50_SECTORS:
        NIFTY50_SECTORS[sec] = []
    NIFTY50_SECTORS[sec].append(sym_raw)


# =============================================================================
# Public API
# =============================================================================

def get_sectors() -> list[str]:
    """Return the list of available sector names (including 'All Sectors' first)."""
    return list(NSE_STOCKS.keys())


def get_symbols(sector: str) -> list[str]:
    """Return all stock symbols (with .NS suffix) for a given sector."""
    return NSE_STOCKS.get(sector, [])


def get_symbol_count(sector: str) -> int:
    """Return the number of stocks in a sector."""
    return len(NSE_STOCKS.get(sector, []))


def get_sector_for_symbol(symbol: str) -> str:
    """
    Return the sector name for a given symbol.

    Parameters
    ----------
    symbol : str
        Symbol with or without .NS suffix (e.g., 'HDFCBANK.NS' or 'HDFCBANK')

    Returns
    -------
    str
        Sector name, or 'Unknown' if not found
    """
    raw = symbol.replace(".NS", "").upper()
    return STOCK_SECTORS.get(raw, "Unknown")


def get_company_name(symbol: str) -> str:
    """
    Return the company name for a given symbol.

    Parameters
    ----------
    symbol : str
        Symbol with or without .NS suffix

    Returns
    -------
    str
        Company name, or the raw symbol if not found
    """
    raw = symbol.replace(".NS", "").upper()
    return COMPANY_NAMES.get(raw, raw)


def get_market_cap(symbol: str) -> str:
    """
    Return market cap classification for a given symbol.

    Parameters
    ----------
    symbol : str
        Symbol with or without .NS suffix

    Returns
    -------
    str
        'Large Cap', 'Mid Cap', or 'Small Cap'
    """
    raw = symbol.replace(".NS", "").upper()
    return MARKET_CAP.get(raw, "Small Cap")


def get_sectoral_index(symbol: str) -> Optional[str]:
    """
    Return the sectoral index for a given symbol, if any.

    Parameters
    ----------
    symbol : str
        Symbol with or without .NS suffix

    Returns
    -------
    str or None
        Sectoral index name (e.g., 'Nifty Bank', 'Nifty IT'), or None
    """
    raw = symbol.replace(".NS", "").upper()
    return SECTORAL_INDICES.get(raw)


def get_nifty50_symbols() -> list[str]:
    """Return the list of Nifty 50 symbols (without .NS suffix)."""
    return sorted(NIFTY50_SYMBOLS)


def is_nifty50(symbol: str) -> bool:
    """Check if a symbol is a Nifty 50 constituent."""
    raw = symbol.replace(".NS", "").upper()
    return raw in NIFTY50_SYMBOLS


def get_nifty50_count() -> int:
    """Return the total number of Nifty 50 constituents in our database."""
    return len(NIFTY50_SYMBOLS)


def get_stock_count() -> int:
    """Return the total number of unique stocks across all sectors."""
    return len(_all_symbols)


# =============================================================================
# Main — Stats
# =============================================================================
if __name__ == "__main__":
    sep = "-" * 30
    sep2 = "-" * 8
    sep3 = "-" * 10
    print("=" * 60)
    print("NSE Stock Database — Statistics")
    print("=" * 60)
    print(f"\nTotal unique stocks: {get_stock_count()}")
    print(f"Nifty 50 constituents: {get_nifty50_count()}")
    print(f"Total sectors: {len(get_sectors())}")
    print(f"Companies with names: {len(COMPANY_NAMES)}")
    print(f"Market cap classified: {len(MARKET_CAP)}")
    print(f"Sectoral indices mapped: {len(SECTORAL_INDICES)}")
    print(f"\nSector Breakdown:")
    print(f"  {'Sector':<30s} {'Stocks':>8s} {'Nifty 50':>10s}")
    print(f"  {sep:<30s} {sep2:>8s} {sep3:>10s}")
    for sec in sorted(get_sectors()):
        if sec == "All Sectors":
            continue
        count = get_symbol_count(sec)
        n50 = len([s for s in NIFTY50_SYMBOLS if STOCK_SECTORS.get(s) == sec])
        print(f"  {sec:<30s} {count:>8d} {n50:>10d}")
    print(f"  {sep:<30s} {sep2:>8s} {sep3:>10s}")
    print(f"  {'All Sectors':<30s} {get_symbol_count('All Sectors'):>8d} {get_nifty50_count():>10d}")
