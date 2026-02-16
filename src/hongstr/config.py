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
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "A").upper()
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "0") == "1"

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
