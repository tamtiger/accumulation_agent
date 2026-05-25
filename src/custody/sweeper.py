import datetime
import logging
from typing import Optional
from src.config import settings
from src.utils.db import get_connection, release_connection
from src.utils.logging import get_agent_logger

logger = get_agent_logger("custody_agent")

class CustodySweeper:
    """
    Monitors trading sleeve balances and detects when to promote excess swing assets to Core cold wallet storage.
    """
    def __init__(self, trading_target: float = 0.15, promotion_threshold_multiplier: float = 1.3):
        self.trading_target = settings.trading_target
        self.promotion_threshold_multiplier = settings.promotion_threshold

    def check_promotion_trigger(self) -> Optional[float]:
        """
        Audits database history over the last 7 days.
        Returns the excess quantity of BTC to be promoted to Core cold storage, or None.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Query portfolio states daily snapshots (last snapshot of each day) in the last 7 days
                cur.execute(
                    """
                    SELECT DISTINCT ON (date_trunc('day', time)) time, trading_btc_qty, core_btc_qty
                    FROM portfolio_states
                    WHERE time >= NOW() - INTERVAL '7 days'
                    ORDER BY date_trunc('day', time) ASC, time DESC
                    """
                )
                rows = cur.fetchall()
                if len(rows) < 7:
                    # Insufficient days of historical data to trigger promotion
                    return None
                
                # Check if trading sleeve exceeded target * threshold consistently
                for row in rows:
                    time_stamp, trading_qty, core_qty = row
                    total_btc = trading_qty + core_qty
                    target_qty = total_btc * self.trading_target
                    threshold = target_qty * self.promotion_threshold_multiplier
                    
                    if trading_qty <= threshold:
                        # Breached target did not hold continuously
                        return None
                
                # Trigger promotion based on the latest snapshot
                latest_trading_qty = rows[-1][1]
                latest_core_qty = rows[-1][2]
                latest_total = latest_trading_qty + latest_core_qty
                
                excess = latest_trading_qty - (latest_total * self.trading_target)
                if excess > 0:
                    logger.critical(
                        f"Core Promotion Rule Triggered: excess={excess:.6f} BTC. "
                        f"Generate promotion transfer request.",
                        action="promotion_signal",
                        metadata={"excess_btc": excess, "trading_qty": latest_trading_qty}
                    )
                    return excess
                return None
        except Exception as e:
            logger.error(f"Error querying promotion database log: {e}")
            return None
        finally:
            release_connection(conn)
