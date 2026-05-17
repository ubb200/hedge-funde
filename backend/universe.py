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
    # Top 10
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "LTC-USD",
    # Layer 1 / Smart Contract
    "ATOM-USD", "NEAR-USD", "ICP-USD", "APT-USD", "SUI-USD",
    "SEI-USD", "TAO-USD", "EGLD-USD", "XTZ-USD", "ALGO-USD",
    "VET-USD", "HBAR-USD", "FLOW-USD", "KSM-USD", "XLM-USD",
    "BCH-USD", "ETC-USD", "DASH-USD", "XMR-USD",
    # Layer 2 / Rollups
    "ARB-USD", "OP-USD", "MATIC-USD", "POL-USD",
    # DeFi
    "UNI-USD", "AAVE-USD", "LDO-USD", "CRV-USD", "SNX-USD",
    "COMP-USD", "YFI-USD", "BAL-USD", "SUSHI-USD", "DYDX-USD",
    "GRT-USD", "RPL-USD", "PENDLE-USD", "ENA-USD", "ONDO-USD",
    # AI / Data
    "FET-USD", "OCEAN-USD", "RENDER-USD",
    # Meme
    "SHIB-USD", "PEPE-USD", "BONK-USD", "WIF-USD", "FLOKI-USD",
    # Gaming / NFT
    "SAND-USD", "MANA-USD", "AXS-USD", "ENJ-USD", "CHZ-USD",
    # Infrastructure / Other
    "FIL-USD", "TIA-USD", "INJ-USD", "JUP-USD", "JTO-USD",
    "PYTH-USD", "WLD-USD", "TRX-USD", "STX-USD", "TON-USD",
    "KAS-USD",
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
