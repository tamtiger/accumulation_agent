import datetime
from src.utils.logging import get_agent_logger
from typing import Dict, List, Tuple
from src.inventory.models import TradeLot, InventoryRepository

logger = get_agent_logger("inventory_ledger")

class FIFOLedger:
    """
    Maintains the FIFO queue of purchased BTC lots and tracks portfolio sleeves balances.
    """
    def __init__(self):
        self.active_lots: List[TradeLot] = []
        self.core_btc_qty: float = 0.0
        self.trading_btc_qty: float = 0.0
        self.reserve_usdt: float = 0.0

    def load_from_db(self) -> None:
        """
        Loads active lots from database to restore state on startup.
        """
        try:
            self.active_lots = InventoryRepository.get_active_lots()
            logger.info(f"Loaded {len(self.active_lots)} active trade lots from database.")
        except Exception as e:
            logger.error(f"Failed to load active lots from database: {e}")
            self.active_lots = []

    @property
    def total_btc_qty(self) -> float:
        return self.core_btc_qty + self.trading_btc_qty

    @property
    def total_portfolio_value_btc(self) -> float:
        return self.total_btc_qty

    @property
    def avg_cost(self) -> float:
        """
        Calculates the average cost basis across all remaining active lots.
        """
        total_qty = sum(lot.qty for lot in self.active_lots)
        if total_qty == 0:
            return 0.0
        total_cost = sum(lot.qty * lot.purchase_price for lot in self.active_lots)
        return total_cost / total_qty

    def add_buy_lot(self, qty: float, price: float, timestamp: datetime.datetime, regime_tag: str) -> None:
        """
        Creates and appends a new lot to the FIFO queue, updating database and balances.
        """
        if qty <= 0:
            return

        lot = TradeLot(
            qty=qty,
            purchase_price=price,
            purchase_time=timestamp,
            regime_tag=regime_tag,
            status="active"
        )
        
        # Save to database
        InventoryRepository.save_lot(lot)
        self.active_lots.append(lot)
        
        # Update trading sleeve and decrease reserve cash
        self.trading_btc_qty += qty
        self.reserve_usdt -= qty * price
        
        logger.info(
            f"BUY lot added: qty={qty:.6f}, price={price:.2f}, new_avg_cost={self.avg_cost:.2f}",
            action="buy_lot_ledger",
            state_snapshot=self.get_state_snapshot()
        )

    def consume_sell_lots(self, qty_to_sell: float, sell_price: float, timestamp: datetime.datetime, order_id: str) -> float:
        """
        Consumes lots from the head of the FIFO queue to fill a sell order.
        Returns the realized PnL in USDT.
        """
        if qty_to_sell <= 0 or not self.active_lots:
            return 0.0

        original_qty_to_sell = qty_to_sell
        realized_pnl = 0.0
        remaining_qty = qty_to_sell
        
        lots_to_remove = []

        for lot in self.active_lots:
            if remaining_qty <= 0:
                break
                
            if lot.qty <= remaining_qty:
                # Consume entire lot
                consumed_qty = lot.qty
                remaining_qty -= lot.qty
                realized_pnl += (sell_price - lot.purchase_price) * consumed_qty
                
                # Update lot status in database
                InventoryRepository.update_lot_status(lot.id, "consumed", 0.0)
                lots_to_remove.append(lot)
                
                logger.debug(f"Lot ID {lot.id} fully consumed. Qty: {consumed_qty:.6f}")
            else:
                # Partially consume lot
                consumed_qty = remaining_qty
                lot.qty -= remaining_qty
                remaining_qty = 0.0
                realized_pnl += (sell_price - lot.purchase_price) * consumed_qty
                
                # Update remaining lot qty in database
                InventoryRepository.update_lot_status(lot.id, "active", lot.qty)
                logger.debug(f"Lot ID {lot.id} partially consumed. Remaining: {lot.qty:.6f}")

        # Remove fully consumed lots from memory list
        for lot in lots_to_remove:
            self.active_lots.remove(lot)

        # Update trading sleeve and increase reserve cash
        self.trading_btc_qty -= original_qty_to_sell
        self.reserve_usdt += original_qty_to_sell * sell_price

        # Save to trade history database
        InventoryRepository.save_trade_history(
            time_val=timestamp,
            order_id=order_id,
            symbol="BTC/USDT",
            side="sell",
            price=sell_price,
            qty=original_qty_to_sell,
            fees=0.0,  # Execution agent will update fees / slippage later
            slippage=0.0,
            pnl=realized_pnl
        )

        logger.info(
            f"SELL ledger updated: qty={original_qty_to_sell:.6f}, price={sell_price:.2f}, realized_pnl={realized_pnl:.2f}",
            action="sell_lot_ledger",
            state_snapshot=self.get_state_snapshot()
        )
        
        return realized_pnl

    def get_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculates unrealized P&L in USDT based on current market price.
        """
        return sum((current_price - lot.purchase_price) * lot.qty for lot in self.active_lots)

    def get_state_snapshot(self) -> Dict[str, float]:
        return {
            "core_btc_qty": self.core_btc_qty,
            "trading_btc_qty": self.trading_btc_qty,
            "reserve_usdt": self.reserve_usdt,
            "avg_cost": self.avg_cost
        }
