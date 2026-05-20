STOCKS = [
    # ── Mega-cap Tech (bekannt, trotzdem im Universum) ──────────────────────
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA",

    # ── KI-Infrastruktur: Picks & Shovels (weniger bekannt) ─────────────────
    "SMCI",         # Super Micro Computer — KI-Server
    "VRT",          # Vertiv — Kühlsysteme für Rechenzentren
    "ETN",          # Eaton — Stromversorgung für Rechenzentren
    "HUBB",         # Hubbell — Netzausrüstung, Grid-Modernisierung
    "ANET",         # Arista Networks — KI-Networking
    "ALAB",         # Astera Labs — KI-Konnektivitätschips
    "CLS",          # Celestica — KI-Server-Fertigung (Kanada)
    "APLD",         # Applied Digital — KI-Rechenzentren (small cap)
    "IREN",         # Iris Energy — GPU-Computing / Mining
    "CRWV",         # CoreWeave — KI-Cloud-Infrastruktur
    "SOUN",         # SoundHound AI — KI-Sprachtechnologie (small cap)
    "BBAI",         # BigBear.ai — KI-Entscheidungssysteme (small cap)
    "LUNR",         # Intuitive Machines — Mondmissionen / Space
    "RKLB",         # Rocket Lab — günstiger Raketenstart (small cap)
    "RDW",          # Redwire — Space-Infrastruktur (small cap)
    "ACHR",         # Archer Aviation — eVTOL / Flugtaxi

    # ── Kernenergie-Renaissance ──────────────────────────────────────────────
    "CCJ",          # Cameco — weltgrösster Uranproduzent (Kanada)
    "UEC",          # Uranium Energy Corp — US-Uran (small cap)
    "UUUU",         # Energy Fuels — Uran + seltene Erden (small cap)
    "LEU",          # Centrus Energy — Urananreicherung (small cap)
    "SMR",          # NuScale Power — kleine Modulreaktoren (small cap)
    "OKLO",         # Oklo — advanced nuclear startup (sehr small cap)
    "BWXT",         # BWX Technologies — Nuklearservices
    "CEG",          # Constellation Energy — grösster US-Kernkraft-Betreiber
    "VST",          # Vistra — Kernkraft + Erdgas, KI-Strom
    "NNE",          # Nano Nuclear Energy — Mikroreaktoren (very small)

    # ── Rüstung & Verteidigung (weniger bekannte) ────────────────────────────
    "KTOS",         # Kratos Defense — autonome Systeme, Drohnen (small cap)
    "BWXT",         # BWX — Nuklear-U-Boote, Reaktoren für Militär
    "HEI",          # Heico — Ersatzteile für Luft- und Raumfahrt
    "TDG",          # TransDigm — Nischenteile für Flugzeuge (Monopol)
    "MRCY",         # Mercury Systems — Defense Electronics (small cap)
    "DCO",          # Ducommun — Aerospace/Defense Komponenten (small cap)
    "MOG-A",        # Moog — Präzisionssteuerung (Defense/Space)
    "LDOS",         # Leidos — Defense IT und KI
    "CACI",         # CACI International — Defense IT
    "PLTR",         # Palantir — KI für Geheimdienste und Militär
    "RTX",          # Raytheon — Raketen, Luftabwehr
    "LHX",          # L3Harris — Defense Electronics

    # ── Rohstoffe für die Zukunft ────────────────────────────────────────────
    "MP",           # MP Materials — US-Seltenerd-Magnete (E-Autos, Wind)
    "FCX",          # Freeport-McMoRan — Kupfer (KI-Rechenzentren, E-Mobilität)
    "SCCO",         # Southern Copper — Kupfer (sehr gross, Mexiko)
    "ALB",          # Albemarle — Lithium für Batterien
    "SQM",          # SQM — Lithium/Kalium (Chile)
    "CPER",         # US Copper Index ETF
    "AA",           # Alcoa — Aluminium (E-Autos, Infrastruktur)
    "X",            # US Steel — Infrastruktur, Reshoring
    "NUE",          # Nucor — Grüner Stahl, Infrastruktur
    "CLF",          # Cleveland-Cliffs — Stahl, E-Auto-Lieferkette

    # ── Biotech / GLP-1 / weniger bekannte ──────────────────────────────────
    "LLY",          # Eli Lilly — GLP-1-Marktführer
    "NVO",          # Novo Nordisk — GLP-1 (Ozempic, Wegovy)
    "VKTX",         # Viking Therapeutics — GLP-1-Pipeline (small cap)
    "GPCR",         # Structure Therapeutics — GLP-1 oral (small cap)
    "RYTM",         # Rhythm Pharmaceuticals — Adipositas (small cap)
    "RVNC",         # Revance Therapeutics — Botox-Alternative (small cap)
    "CALT",         # Calliditas Therapeutics — Nischen-Biotech
    "ARQT",         # Arcutis Biotherapeutics — Dermatologie (small cap)
    "RXRX",         # Recursion Pharma — KI-Wirkstoffforschung
    "BMRN",         # BioMarin — seltene Krankheiten
    "IONS",         # Ionis Pharmaceuticals — RNA-Therapeutika

    # ── Energie-Infrastruktur / Grid-Modernisierung ──────────────────────────
    "PWR",          # Quanta Services — Stromnetz-Bau (KI-Rechenzentren brauchen Grid)
    "FIX",          # Comfort Systems — HVAC für Rechenzentren (small-mid cap)
    "AAON",         # AAON — Klimaanlagen für Rechenzentren (small cap)
    "EME",          # EMCOR — Elektro/Mechanik für Grossprojekte
    "MTZ",          # MasTec — Infrastrukturbau (5G, Grid, EV-Ladestationen)
    "WLDN",         # Willdan Group — Energieeffizienz-Beratung (very small)

    # ── Cybersecurity ────────────────────────────────────────────────────────
    "CRWD",         # CrowdStrike — KI-basierte Cybersecurity
    "PANW",         # Palo Alto Networks
    "ZS",           # Zscaler — Zero Trust
    "NET",          # Cloudflare — Edge-Netzwerk
    "S",            # SentinelOne — KI-Endpoint-Security (mid cap)
    "CYBR",         # CyberArk — Identitätssicherheit (Israel)

    # ── Finance / FinTech ────────────────────────────────────────────────────
    "JPM", "GS", "V", "MA", "COIN", "HOOD", "SOFI", "AFRM",
    "PYPL", "BILL", "SMAR",

    # ── Consumer / Retail ────────────────────────────────────────────────────
    "WMT", "COST", "AMZN", "BKNG", "ABNB", "UBER",

    # ── Klassische Industrials ───────────────────────────────────────────────
    "CAT", "DE", "GE", "HON", "ITW",

    # ── International ────────────────────────────────────────────────────────
    "ASML",         # ASML — EUV-Lithographie (Chipfertigung-Monopol)
    "TSM",          # TSMC — weltbeste Chipfertigung
    "ARM",          # ARM Holdings — Chip-Designs (KI-Edge)
    "SAP",          # SAP — Enterprise-Software
    "SHOP",         # Shopify — E-Commerce Infrastruktur

    # ── Sonstige Megatrend-Plays ─────────────────────────────────────────────
    "MSTR",         # MicroStrategy — Bitcoin-Proxy
    "SNOW",         # Snowflake — Daten-Cloud für KI
    "DDOG",         # Datadog — KI-Monitoring/Observability
    "MDB",          # MongoDB — Datenbank für KI-Apps
    "NOW",          # ServiceNow — KI-Workflow-Automation
    "AXON",         # Axon — Taser + KI-Körperkameras (Defense/Police)
    "RGEN",         # Repligen — Biotech-Zulieferer (Filtration) (small cap)
    "TREX",         # Trex — Verbundholz (Reshoring, Infrastruktur)
]

CRYPTO = [
    # Top Coins
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "LTC-USD",
    # Layer 1 / Smart Contract
    "ATOM-USD", "NEAR-USD", "APT-USD", "SUI-USD",
    "TAO-USD", "HBAR-USD", "XLM-USD", "BCH-USD",
    # Layer 2
    "ARB-USD", "OP-USD", "POL-USD",
    # DeFi
    "UNI-USD", "AAVE-USD", "LDO-USD", "CRV-USD",
    "GRT-USD", "PENDLE-USD", "ENA-USD", "ONDO-USD",
    # AI / Data
    "FET-USD", "RENDER-USD", "OCEAN-USD",
    # Meme
    "SHIB-USD", "PEPE-USD", "WIF-USD",
    # Infrastructure
    "FIL-USD", "INJ-USD", "TRX-USD", "STX-USD", "TON-USD", "KAS-USD",
]

ETFS = [
    # US Breit
    "SPY", "QQQ", "VTI", "IWM",
    # International
    "VEA", "VWO", "EEM",
    # Sektor
    "XLK", "XLF", "XLV", "XLE", "XLI", "XLB", "XLU",
    # Bonds
    "TLT", "IEF", "HYG",
    # Thematisch
    "ARKK", "BOTZ", "ROBO", "AIQ", "HACK",
    # Kernenergie/Uran
    "URA",          # Global X Uranium ETF
    "NLR",          # VanEck Uranium+Nuclear ETF
    # KI
    "IRBO",         # iShares Robotics & AI ETF
    "WTAI",         # WisdomTree AI ETF
    # Defense
    "ITA",          # iShares US Aerospace & Defense ETF
    "XAR",          # SPDR Aerospace & Defense ETF
    # Clean Energy
    "ICLN", "QCLN",
    # Rohstoffe
    "GLD", "SLV", "COPX",  # Global X Copper Miners
    "URNM",         # Sprott Uranium Miners ETF
    # REITs (Rechenzentren)
    "EQIX", "DLR",  # Equinix, Digital Realty — Rechenzentrum-REITs
]

ALL_SYMBOLS: list[str] = list(dict.fromkeys(STOCKS + CRYPTO + ETFS))
