import os
import json
import datetime
from typing import Dict, Any, Optional
from src.config import settings
from src.utils.logging import get_agent_logger
from src.inventory.ledger import FIFOLedger
from src.portfolio.tracker import PortfolioTracker
from src.monitoring.exporter import TelegramNotifier

logger = get_agent_logger("reconcile_audit")

class LedgerAuditor:
    """
    Handles automated daily ledger audits and reconciliation reports.
    """
    def __init__(self, ccxt_exchange: Any, notifier: Optional[TelegramNotifier] = None):
        self.exchange = ccxt_exchange
        self.notifier = notifier or TelegramNotifier()
        self.tracker = PortfolioTracker(hot_exchange_cap=settings.hot_exchange_cap)
        self.ledger = FIFOLedger()

    def run_daily_audit(self) -> Dict[str, Any]:
        """
        Executes daily balance audit check and saves report.
        """
        logger.info("Executing daily ledger audit...")
        
        # 1. Fetch live balances
        try:
            live_bal = self.exchange.fetch_balance()
            exchange_usdt = float(live_bal["free"].get("USDT", 0.0))
            exchange_btc = float(live_bal["free"].get("BTC", 0.0))
        except Exception as e:
            logger.error(f"Failed to query live exchange balances: {e}")
            raise e

        # 2. Fetch database state
        self.ledger.load_from_db()
        db_state = self.ledger.get_state_snapshot()
        db_usdt = db_state["reserve_usdt"]
        db_btc = db_state["trading_btc_qty"]
        
        # 3. Calculate discrepancy percentages
        usdt_discrepancy = 0.0
        if db_usdt > 0:
            usdt_discrepancy = abs(exchange_usdt - db_usdt) / db_usdt
        elif exchange_usdt > 0:
            usdt_discrepancy = 1.0

        btc_discrepancy = 0.0
        if db_btc > 0:
            btc_discrepancy = abs(exchange_btc - db_btc) / db_btc
        elif exchange_btc > 0:
            btc_discrepancy = 1.0

        # Enforce strict zero discrepancy threshold (1e-5 tolerance)
        has_discrepancy = (usdt_discrepancy > 1e-5) or (btc_discrepancy > 1e-5)
        
        report = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "exchange": {
                "USDT": exchange_usdt,
                "BTC": exchange_btc
            },
            "database": {
                "USDT": db_usdt,
                "BTC": db_btc
            },
            "discrepancies": {
                "USDT_pct": usdt_discrepancy * 100.0,
                "BTC_pct": btc_discrepancy * 100.0
            },
            "audit_passed": not has_discrepancy
        }

        # 4. Save report
        os.makedirs("data/audits", exist_ok=True)
        filename = f"data/audits/audit_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=4)
            
        logger.info(f"Daily audit report saved to {filename}")

        # 5. Alert on mismatch
        if has_discrepancy:
            err_msg = (
                f"Ledger Discrepancy Alert! Daily audit failed. "
                f"USDT discrepancy: {usdt_discrepancy*100:.4f}% "
                f"(Exchange: {exchange_usdt:.2f}, DB: {db_usdt:.2f}). "
                f"BTC discrepancy: {btc_discrepancy*100:.4f}% "
                f"(Exchange: {exchange_btc:.6f}, DB: {db_btc:.6f})."
            )
            logger.critical(err_msg, action="audit_discrepancy_failure")
            self.notifier.send_alert(err_msg)
            
        return report
