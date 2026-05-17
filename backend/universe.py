STOCKS = [
    # Mega-cap Tech
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "V", "MA", "SCHW",
    "BLK", "SPGI", "CB", "AON",
    # Healthcare
    "JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR",
    "BMY", "GILD", "AMGN", "REGN", "SYK", "MDT", "ELV", "HCA", "CI", "ZTS",
    # Consumer
    "PG", "KO", "PEP", "WMT", "COST", "MCD", "SBUX", "NKE", "TJX",
    "HD", "LOW", "TGT", "BKNG", "DIS", "NFLX",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX",
    # Industrials
    "GE", "HON", "CAT", "RTX", "DE", "UPS", "ITW", "EMR", "TDG",
    # Semis / Software
    "ORCL", "CRM", "ADBE", "INTC", "AMD", "QCOM", "TXN", "AMAT",
    "MU", "ADI", "NOW", "IBM", "CSCO", "ACN",
    # Telecom
    "VZ", "T",
    # Materials / Utilities / REITs
    "LIN", "APD", "NEE", "DUK", "SO", "PLD", "AMT",
    # Other large-cap
    "ISRG", "BRK-B", "PM", "MO",
    # International (US-listed)
    "ASML", "SAP", "NVO", "TM", "TSM", "SONY", "BABA",
    # Growth / Mid-cap
    "PLTR", "SNOW", "COIN", "MSTR", "RBLX", "RIVN", "ARM", "SMCI",
    "UBER", "LYFT", "DASH", "ABNB", "SHOP", "PYPL", "ROKU",
    "SPOT", "TWLO", "DDOG", "NET", "ZS", "CRWD", "PANW", "FTNT",
    "OKTA", "MDB", "GTLB", "BILL", "HOOD", "SOFI", "AFRM",
]

CRYPTO = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
    "ATOM-USD", "LTC-USD", "BCH-USD",
    "NEAR-USD", "FIL-USD", "ALGO-USD", "VET-USD",
    "ICP-USD", "HBAR-USD", "ARB-USD", "OP-USD", "INJ-USD",
    "TIA-USD", "SEI-USD", "SHIB-USD",
]

ETFS = [
    # US broad market
    "SPY", "QQQ", "VTI", "VOO", "IVV", "IWM", "DIA", "MDY", "IJR",
    # International
    "VEA", "VWO", "EEM", "EFA", "VXUS", "IEUR", "MCHI",
    # Sector
    "XLK", "XLF", "XLV", "XLE", "XLY", "XLI", "XLB", "XLP", "XLU", "XLC", "XLRE",
    # Bonds
    "TLT", "IEF", "SHY", "HYG", "LQD", "AGG",
    # Thematic / Factor
    "ARKK", "ARKG", "ARKW", "KWEB", "SCHD", "JEPI", "JEPQ", "VIG", "DGRO",
    "BOTZ", "ROBO", "AIQ", "HACK", "WCLD",
    # Commodities
    "GLD", "SLV", "USO", "DBC", "PDBC",
    # Real Estate
    "VNQ", "IYR",
]

ALL_SYMBOLS: list[str] = list(dict.fromkeys(STOCKS + CRYPTO + ETFS))
