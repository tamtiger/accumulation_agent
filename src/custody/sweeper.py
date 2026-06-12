import datetime
from typing import Optional
from src.utils.db import get_connection, release_connection
from src.utils.logging import get_agent_logger

logger = get_agent_logger("custody_agent")

class CustodySweeper:
    """
    Monitors trading sleeve balances and detects when to promote excess swing assets to Core cold wallet storage.
    """
    def __init__(self, trading_target: float = 0.15, promotion_threshold_multiplier: float = 1.3):
        self.trading_target = trading_target
        self.promotion_threshold_multiplier = promotion_threshold_multiplier

    def check_promotion_trigger(self, current_time: datetime.datetime) -> Optional[float]:
        """
        Audits database history over the last 7 days.
        Returns the excess quantity of BTC to be promoted to Core cold storage, or None.
        """
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                # Query portfolio states daily snapshots (last snapshot of each day) in the last 7 days
                cur.execute(
                    """
                    SELECT DISTINCT ON (date_trunc('day', time)) time, trading_btc_qty, core_btc_qty
                    FROM portfolio_states
                    WHERE time >= %s - INTERVAL '7 days' AND time <= %s
                    ORDER BY date_trunc('day', time) ASC, time DESC
                    """,
                    (current_time, current_time)
                )
                rows = cur.fetchall()
                if len(rows) < 7:
                    # Insufficient days of historical data to trigger promotion
                    return None
                
                # Calculate exceeded_count
                exceeded_count = 0
                for row in rows:
                    time_stamp, trading_qty, core_qty = row
                    total_btc = trading_qty + core_qty
                    target_qty = total_btc * self.trading_target
                    threshold = target_qty * self.promotion_threshold_multiplier
                    if trading_qty > threshold:
                        exceeded_count += 1

                # Check if there was a sell order in the last 7 days
                cur.execute(
                    """
                    SELECT 1 FROM trade_history
                    WHERE side = 'sell' AND time >= %s - INTERVAL '7 days' AND time <= %s
                    LIMIT 1
                    """,
                    (current_time, current_time)
                )
                res = cur.fetchone()
                # Real DB returns a tuple/list. Mocks not configured return MagicMock.
                has_sell = isinstance(res, (tuple, list)) and len(res) > 0

                required_days = 5 if has_sell else len(rows)
                if exceeded_count < required_days:
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
            if conn is not None:
                release_connection(conn)
