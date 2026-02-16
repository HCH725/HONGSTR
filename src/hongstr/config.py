import os
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv()

# Paths
opt_project_root = os.getenv("PROJECT_ROOT")
if opt_project_root:
    PROJECT_ROOT = Path(opt_project_root)
else:
    PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"

# Timezone
TIMEZONE = "Asia/Taipei"

# Phase 0 Constants
# Enforce 1h/4h for HONG
# Enforce 1h/4h for HONG
HONG_TIMEFRAMES = ["1h", "4h"]
PORTFOLIO_ID = os.getenv("PORTFOLIO_ID", "HONG")

# Data
REQUIRED_DERIVED_TFS = ["5m", "15m", "1h", "4h"]

# Execution
# Modes: A=Backtest, B=Paper, C=Testnet
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "B").upper() # Default to Paper
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "0") == "1"
EXECUTION_STATE_DIR = os.getenv("EXECUTION_STATE_DIR", str(DATA_DIR / "state"))
EXECUTION_PAPER_DIR = os.getenv("EXECUTION_PAPER_DIR", str(DATA_DIR / "paper"))

# Risk
LEVERAGE_DEFAULT = int(os.getenv("LEVERAGE_DEFAULT", "2"))
LEVERAGE_MAX = int(os.getenv("LEVERAGE_MAX", "3"))
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", "3"))
MAX_TOTAL_EXPOSURE_PCT = float(os.getenv("MAX_TOTAL_EXPOSURE_PCT", "0.95")) # 95%
POSITION_SIZE_PCT_DEFAULT = float(os.getenv("POSITION_SIZE_PCT_DEFAULT", "0.1")) # 10% per trade

# Alerts
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID", TELEGRAM_CHAT_ID)

# Binance Testnet
BINANCE_TESTNET_BASE_URL = os.getenv("BINANCE_TESTNET_BASE_URL", "https://testnet.binancefuture.com")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# Reconcile
RECONCILE_INTERVAL_SEC = int(os.getenv("RECONCILE_INTERVAL_SEC", "10"))

# Realtime Feeds (C7)
REALTIME_ENABLED = os.getenv("REALTIME_ENABLED", "true").lower() == "true"
REALTIME_SYMBOLS = os.getenv("REALTIME_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT").split(",")
REALTIME_STREAMS = os.getenv("REALTIME_STREAMS", "aggTrade,kline_1m").split(",")
REALTIME_OUT_DIR = os.getenv("REALTIME_OUT_DIR", str(DATA_DIR / "realtime"))
REALTIME_WS_BASE = os.getenv("REALTIME_WS_BASE", "wss://stream.binance.com:9443/stream")
REALTIME_RUN_SECONDS = int(os.getenv("REALTIME_RUN_SECONDS", "30"))
REALTIME_RECONNECT_MAX_DELAY = int(os.getenv("REALTIME_RECONNECT_MAX_DELAY", "60"))

# Signal Engine (C8)
SIGNAL_ENABLED = os.getenv("SIGNAL_ENABLED", "true").lower() == "true"
SIGNAL_TFS = os.getenv("SIGNAL_TFS", "1m,5m,15m,1h,4h").split(",")
SIGNAL_INPUT_ROOT = os.getenv("SIGNAL_INPUT_ROOT", REALTIME_OUT_DIR)
SIGNAL_OUTPUT_ROOT = os.getenv("SIGNAL_OUTPUT_ROOT", str(DATA_DIR / "signals"))
SIGNAL_STATE_ROOT = os.getenv("SIGNAL_STATE_ROOT", str(DATA_DIR / "state"))
SIGNAL_ENGINE_MODE = os.getenv("SIGNAL_ENGINE_MODE", "tail_jsonl")
SIGNAL_MAX_BARS = int(os.getenv("SIGNAL_MAX_BARS", "2000"))

# Strategy (C9)
STRATEGY_ENABLED = os.getenv("STRATEGY_ENABLED", "true").lower() == "true"
STRATEGY_LIST = os.getenv("STRATEGY_LIST", "vwap_supertrend,rsi_divergence,macd_divergence").split(",")
STRATEGY_TIMEFRAME_BASE = os.getenv("STRATEGY_TIMEFRAME_BASE", "1m")
STRATEGY_TIMEFRAME_SIGNAL = os.getenv("STRATEGY_TIMEFRAME_SIGNAL", "1h")

# Strategy Params
ST_ATR_PERIOD = int(os.getenv("ST_ATR_PERIOD", "10"))
ST_ATR_MULT = float(os.getenv("ST_ATR_MULT", "3.0"))
VWAP_ANCHOR = os.getenv("VWAP_ANCHOR", "session") # session or day
VWAP_BAND_STD = float(os.getenv("VWAP_BAND_STD", "1.0"))

RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
DVG_LOOKBACK = int(os.getenv("DVG_LOOKBACK", "50"))
DVG_PIVOT_LEFT = int(os.getenv("DVG_PIVOT_LEFT", "3"))
DVG_PIVOT_RIGHT = int(os.getenv("DVG_PIVOT_RIGHT", "3"))

MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))
