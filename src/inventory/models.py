import datetime
import logging
from typing import Any, Dict, List, Optional
from src.utils.db import get_connection, release_connection

logger = logging.getLogger("inventory_models")

class TradeLot:
    """
    Represents an individual purchased BTC lot tracked via FIFO.
    """
    def __init__(self, qty: float, purchase_price: float, purchase_time: datetime.datetime, regime_tag: str, id: Optional[int] = None, status: str = "active"):
        self.id = id
        self.qty = qty
        self.purchase_price = purchase_price
        self.purchase_time = purchase_time
        self.regime_tag = regime_tag
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "qty": self.qty,
            "purchase_price": self.purchase_price,
            "purchase_time": self.purchase_time.isoformat() if isinstance(self.purchase_time, datetime.datetime) else self.purchase_time,
            "regime_tag": self.regime_tag,
            "status": self.status
        }

class InventoryRepository:
    """
    Repository class using raw SQL to interface with TimescaleDB/PostgreSQL.
    """
    @staticmethod
    def save_lot(lot: TradeLot) -> int:
        """
        Inserts a new trade lot and returns its database ID.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_lots (qty, purchase_price, purchase_time, regime_tag, status)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (lot.qty, lot.purchase_price, lot.purchase_time, lot.regime_tag, lot.status)
                )
                conn.commit()
                lot_id = cur.fetchone()[0]
                lot.id = lot_id
                return lot_id
        except Exception as e:
            logger.error(f"SQL Error in save_lot: {e}")
            raise e
        finally:
            release_connection(conn)

    @staticmethod
    def update_lot_status(lot_id: int, status: str, qty: float) -> None:
        """
        Updates an existing lot status and quantity.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE trade_lots
                    SET status = %s, qty = %s
                    WHERE id = %s
                    """,
                    (status, qty, lot_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQL Error in update_lot_status: {e}")
            raise e
        finally:
            release_connection(conn)

    @staticmethod
    def get_active_lots() -> List[TradeLot]:
        """
        Retrieves all currently active (unconsumed) trade lots ordered chronologically.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, qty, purchase_price, purchase_time, regime_tag, status
                    FROM trade_lots
                    WHERE status = 'active'
                    ORDER BY purchase_time ASC
                    """
                )
                rows = cur.fetchall()
                lots = []
                for row in rows:
                    lots.append(TradeLot(
                        id=row[0],
                        qty=row[1],
                        purchase_price=row[2],
                        purchase_time=row[3],
                        regime_tag=row[4],
                        status=row[5]
                    ))
                return lots
        except Exception as e:
            logger.error(f"SQL Error in get_active_lots: {e}")
            return []
        finally:
            release_connection(conn)

    @staticmethod
    def save_portfolio_state(time_val: datetime.datetime, core_btc: float, trading_btc: float, reserve_usdt: float, total_val: float, regime: int, confidence: float) -> None:
        """
        Persists a tick-by-tick portfolio balance snapshot.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_states (time, core_btc_qty, trading_btc_qty, reserve_usdt, total_portfolio_val_usdt, active_regime, regime_confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (time_val, core_btc, trading_btc, reserve_usdt, total_val, regime, confidence)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQL Error in save_portfolio_state: {e}")
            raise e
        finally:
            release_connection(conn)

    @staticmethod
    def get_latest_portfolio_state() -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest saved portfolio state snapshot.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT time, core_btc_qty, trading_btc_qty, reserve_usdt, total_portfolio_val_usdt, active_regime, regime_confidence
                    FROM portfolio_states
                    ORDER BY time DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    return {
                        "time": row[0],
                        "core_btc_qty": row[1],
                        "trading_btc_qty": row[2],
                        "reserve_usdt": row[3],
                        "total_portfolio_val_usdt": row[4],
                        "active_regime": row[5],
                        "regime_confidence": row[6]
                    }
                return None
        except Exception as e:
            logger.error(f"SQL Error in get_latest_portfolio_state: {e}")
            return None
        finally:
            release_connection(conn)


    @staticmethod
    def save_trade_history(time_val: datetime.datetime, order_id: str, symbol: str, side: str, price: float, qty: float, fees: float, slippage: float, pnl: float) -> None:
        """
        Logs details of completed trade execution.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_history (time, order_id, symbol, side, price, qty, fees, slippage, realized_pnl)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (time_val, order_id, symbol, side, price, qty, fees, slippage, pnl)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQL Error in save_trade_history: {e}")
            raise e
        finally:
            release_connection(conn)

    @staticmethod
    def save_tax_record(
        sell_time: datetime.datetime,
        sell_price: float,
        sell_qty: float,
        lot_purchase_time: datetime.datetime,
        lot_purchase_price: float,
        realized_pnl_usd: float,
        holding_period_days: int,
        order_id: str
    ) -> None:
        """
        Saves a matched tax lot transaction record.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tax_records (sell_time, sell_price, sell_qty, lot_purchase_time, lot_purchase_price, realized_pnl_usd, holding_period_days, order_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (sell_time, sell_price, sell_qty, lot_purchase_time, lot_purchase_price, realized_pnl_usd, holding_period_days, order_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQL Error in save_tax_record: {e}")
            raise e
        finally:
            release_connection(conn)

    @staticmethod
    def get_tax_records() -> List[Dict[str, Any]]:
        """
        Retrieves all tax records chronologically by sell_time.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sell_time, sell_price, sell_qty, lot_purchase_time, lot_purchase_price, realized_pnl_usd, holding_period_days, order_id
                    FROM tax_records
                    ORDER BY sell_time ASC
                    """
                )
                rows = cur.fetchall()
                records = []
                for row in rows:
                    records.append({
                        "sell_date": row[0],
                        "sell_price": row[1],
                        "sell_qty": row[2],
                        "lot_purchase_date": row[3],
                        "lot_purchase_price": row[4],
                        "realized_pnl_usd": row[5],
                        "holding_period_days": row[6],
                        "order_id": row[7]
                    })
                return records
        except Exception as e:
            logger.error(f"SQL Error in get_tax_records: {e}")
            return []
        finally:
            release_connection(conn)
