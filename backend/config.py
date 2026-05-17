from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

DATABASE_PATH = os.getenv("DATABASE_PATH", "./hedge_fund.db")
STARTING_CAPITAL_CHF = float(os.getenv("STARTING_CAPITAL_CHF", "100000.0"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.10"))
CRYPTO_MAX_ALLOCATION = float(os.getenv("CRYPTO_MAX_ALLOCATION", "0.30"))
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

AUTO_TRADE_ENABLED = os.getenv("AUTO_TRADE_ENABLED", "true").lower() == "true"
AUTO_TRADE_HOUR = int(os.getenv("AUTO_TRADE_HOUR", "9"))

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "watchlist.json")

# Kraken Live Trading (nur Krypto)
KRAKEN_API_KEY     = os.getenv("KRAKEN_API_KEY", "")
KRAKEN_API_SECRET  = os.getenv("KRAKEN_API_SECRET", "")
KRAKEN_LIVE_ENABLED = os.getenv("KRAKEN_LIVE_ENABLED", "false").lower() == "true"
KRAKEN_TRADE_SIZE_EUR   = float(os.getenv("KRAKEN_TRADE_SIZE_EUR", "50.0"))
KRAKEN_MIN_CONFIDENCE   = float(os.getenv("KRAKEN_MIN_CONFIDENCE", "0.85"))
KRAKEN_MIN_SCORE        = float(os.getenv("KRAKEN_MIN_SCORE", "0.65"))
