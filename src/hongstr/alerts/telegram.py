import requests
import time
import logging
from hongstr.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ALERT_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramAlerter:
    _last_sent = 0
    _rate_limit_sec = 1.0 # Simple rate limit

    @staticmethod
    def send_message(text: str, level: str = "INFO", context: dict = None):
        """
        Send Telegram message to configured chat.
        level: INFO, WARN, CRIT
        """
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram token not set. Skipping alert.")
            return

        chat_id = TELEGRAM_ALERT_CHAT_ID if level == "CRIT" else TELEGRAM_CHAT_ID
        if not chat_id:
             logger.warning("Telegram chat ID not set. Skipping alert.")
             return

        # Rate Limit
        now = time.time()
        if now - TelegramAlerter._last_sent < TelegramAlerter._rate_limit_sec:
            time.sleep(TelegramAlerter._rate_limit_sec)

        # Format message
        icon = "ℹ️"
        if level == "WARN": icon = "⚠️"
        if level == "CRIT": icon = "🚨"
        
        msg = f"{icon} [{level}] {text}"
        if context:
            msg += "\nContext:\n" + "\n".join([f"{k}: {v}" for k,v in context.items()])

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code != 200:
                logger.error(f"Telegram send failed: {resp.text}")
            else:
                TelegramAlerter._last_sent = time.time()
        except Exception as e:
            logger.error(f"Telegram exception: {e}")

def send_alert(text: str, level: str = "INFO", context: dict = None):
    TelegramAlerter.send_message(text, level, context)
