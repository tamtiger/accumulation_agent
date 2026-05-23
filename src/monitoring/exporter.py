import logging
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Optional
from prometheus_client import Gauge, Counter
from src.config import settings
from src.utils.logging import get_agent_logger

logger = get_agent_logger("monitoring_agent")

# Register Prometheus metrics
loop_latency = Gauge("abas_loop_latency_ms", "Tick cycle latency of orchestrator loop in milliseconds", ["agent_name"])
order_slippage = Gauge("abas_execution_slippage", "Slippage ratio of completed trade fills")
portfolio_balance = Gauge("abas_portfolio_balance", "Current balances of portfolio sleeves", ["sleeve", "asset"])
api_error_counter = Counter("abas_api_errors_total", "Total API errors logged", ["exchange"])
invariant_violation_counter = Counter("abas_invariant_violations_total", "Total trading invariant breaches detected")

class TelegramNotifier:
    """
    Sends emergency notifications and status updates to operators via Telegram API.
    """
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    def send_alert(self, message: str) -> bool:
        """
        Dispatches message to Telegram chat. Falls back to a warning log if credentials are not configured.
        """
        # Clean formatting
        full_message = f"🚨 **ABAS v2 ALERT** 🚨\n\n{message}"
        
        if not self.bot_token or not self.chat_id:
            logger.warning(
                f"[Telegram Alert Fallback]: {message}",
                action="telegram_alert_fallback",
                metadata={"message": message}
            )
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": full_message,
            "parse_mode": "Markdown"
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            # 5-second timeout to avoid blocking execution loop
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode())
                if res.get("ok"):
                    logger.info("Telegram notification sent successfully.", action="telegram_alert_sent")
                    return True
                else:
                    logger.error(f"Telegram API error response: {res}")
                    return False
        except Exception as e:
            logger.error(f"Failed to deliver Telegram notification: {e}")
            return False
