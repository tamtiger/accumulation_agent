import logging
from typing import Dict, Any
from src.utils.logging import get_agent_logger

logger = get_agent_logger("portfolio_agent")

class PortfolioTracker:
    """
    Tracks portfolio exposures across sleeves and reconciles local ledger database balances against exchange values.
    """
    def __init__(self, hot_exchange_cap: float = 0.25):
        self.hot_exchange_cap = hot_exchange_cap

    def reconcile_balances(
        self,
        exchange_usdt: float,
        exchange_btc: float,
        db_reserve_usdt: float,
        db_trading_btc: float
    ) -> bool:
        """
        Reconciles exchange balances with the database buckets.
        Returns False if discrepancy is > 0.01% (0.0001), triggering a ledger discrepancy warning.
        """
        usdt_discrepancy = 0.0
        if db_reserve_usdt > 0:
            usdt_discrepancy = abs(exchange_usdt - db_reserve_usdt) / db_reserve_usdt
        elif exchange_usdt > 0:
            usdt_discrepancy = 1.0

        btc_discrepancy = 0.0
        if db_trading_btc > 0:
            btc_discrepancy = abs(exchange_btc - db_trading_btc) / db_trading_btc
        elif exchange_btc > 0:
            btc_discrepancy = 1.0

        reconciliation_passed = True

        if usdt_discrepancy > 0.0001:
            logger.error(
                f"Ledger Discrepancy Event! USDT discrepancy: {usdt_discrepancy * 100:.4f}% "
                f"(Exchange: {exchange_usdt:.2f}, DB: {db_reserve_usdt:.2f})",
                action="ledger_discrepancy_event",
                metadata={"sleeve": "USDT", "exchange": exchange_usdt, "db": db_reserve_usdt}
            )
            reconciliation_passed = False

        if btc_discrepancy > 0.0001:
            logger.error(
                f"Ledger Discrepancy Event! BTC discrepancy: {btc_discrepancy * 100:.4f}% "
                f"(Exchange: {exchange_btc:.6f}, DB: {db_trading_btc:.6f})",
                action="ledger_discrepancy_event",
                metadata={"sleeve": "BTC", "exchange": exchange_btc, "db": db_trading_btc}
            )
            reconciliation_passed = False

        if reconciliation_passed:
            logger.info(
                f"Ledger reconciliation passed. USDT diff={usdt_discrepancy*100:.4f}%, BTC diff={btc_discrepancy*100:.4f}%",
                action="reconciliation_success"
            )

        return reconciliation_passed

    def monitor_exposure(
        self,
        trading_btc_qty: float,
        core_btc_qty: float,
        reserve_usdt: float,
        btc_price: float
    ) -> float:
        """
        Recomputes hot exchange exposure and warns if it exceeds cap (INV-7).
        """
        total_btc = trading_btc_qty + core_btc_qty
        total_portfolio_value_usdt = reserve_usdt + total_btc * btc_price
        
        if total_portfolio_value_usdt <= 0:
            return 0.0

        exchange_exposure_usdt = trading_btc_qty * btc_price
        exposure_pct = exchange_exposure_usdt / total_portfolio_value_usdt

        if exposure_pct > self.hot_exchange_cap:
            logger.warning(
                f"Exchange Exposure Alert! Current: {exposure_pct * 100:.2f}% (Cap: {self.hot_exchange_cap * 100:.1f}%)",
                action="hot_exposure_warning",
                metadata={"exposure_pct": exposure_pct, "cap": self.hot_exchange_cap}
            )

        return exposure_pct
