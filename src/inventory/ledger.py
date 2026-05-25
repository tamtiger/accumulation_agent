import datetime
import csv
from src.utils.logging import get_agent_logger
from typing import Dict, List, Tuple, Any
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
        Loads active lots and the latest portfolio state from database to restore state on startup.
        """
        try:
            self.active_lots = InventoryRepository.get_active_lots()
            logger.info(f"Loaded {len(self.active_lots)} active trade lots from database.")
            
            latest_state = InventoryRepository.get_latest_portfolio_state()
            if latest_state:
                self.core_btc_qty = latest_state.get("core_btc_qty", 0.0)
                logger.info(f"Restored core_btc_qty from database: {self.core_btc_qty:.6f} BTC")
            else:
                self.core_btc_qty = 0.0
                logger.info("No prior portfolio state found. Initializing core_btc_qty to 0.0")
        except Exception as e:
            logger.error(f"Failed to load active lots or portfolio state from database: {e}")
            self.active_lots = []
            self.core_btc_qty = 0.0

    @property
    def total_btc_qty(self) -> float:
        return self.core_btc_qty + self.trading_btc_qty

    @property
    def total_portfolio_value_btc(self) -> float:
        return self.total_btc_qty

    @property
    def avg_cost(self) -> float:
        """
        Calculates the average cost basis across all remaining active lots (avg_cost_portfolio).
        """
        total_qty = sum(lot.qty for lot in self.active_lots)
        if total_qty == 0:
            return 0.0
        total_cost = sum(lot.qty * lot.purchase_price for lot in self.active_lots)
        return total_cost / total_qty

    @property
    def avg_cost_fifo_lot(self) -> float:
        """
        Calculates the purchase price of the current FIFO head lot (avg_cost_fifo_lot).
        """
        if self.active_lots:
            return self.active_lots[0].purchase_price
        return 0.0

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
                
            consumed_qty = min(lot.qty, remaining_qty)
            
            # Match naive vs tz-aware datetime for calculating holding period
            purchase_t = lot.purchase_time
            if purchase_t.tzinfo is None and timestamp.tzinfo is not None:
                purchase_t = purchase_t.replace(tzinfo=datetime.timezone.utc)
            elif purchase_t.tzinfo is not None and timestamp.tzinfo is None:
                purchase_t = purchase_t.replace(tzinfo=None)
                
            holding_days = (timestamp - purchase_t).days
            lot_pnl_usd = (sell_price - lot.purchase_price) * consumed_qty
            
            # Save tax record
            InventoryRepository.save_tax_record(
                sell_time=timestamp,
                sell_price=sell_price,
                sell_qty=consumed_qty,
                lot_purchase_time=lot.purchase_time,
                lot_purchase_price=lot.purchase_price,
                realized_pnl_usd=lot_pnl_usd,
                holding_period_days=holding_days,
                order_id=order_id
            )
            
            if lot.qty <= remaining_qty:
                # Consume entire lot
                remaining_qty -= lot.qty
                realized_pnl += (sell_price - lot.purchase_price) * consumed_qty
                
                # Update lot status in database
                InventoryRepository.update_lot_status(lot.id, "consumed", 0.0)
                lots_to_remove.append(lot)
                
                logger.debug(f"Lot ID {lot.id} fully consumed. Qty: {consumed_qty:.6f}")
            else:
                # Partially consume lot
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
            "avg_cost": self.avg_cost,
            "avg_cost_fifo_lot": self.avg_cost_fifo_lot
        }

    def export_tax_report_csv(self, filepath: str) -> None:
        """
        Exports all FIFO matched tax transactions to a CSV file compatible with standard crypto tax platforms.
        """
        records = InventoryRepository.get_tax_records()
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sell_date", "sell_price", "sell_qty", 
                "lot_purchase_date", "lot_purchase_price", 
                "realized_pnl_usd", "holding_period_days", "order_id"
            ])
            for r in records:
                sell_date_str = r["sell_date"].isoformat() if isinstance(r["sell_date"], datetime.datetime) else str(r["sell_date"])
                purchase_date_str = r["lot_purchase_date"].isoformat() if isinstance(r["lot_purchase_date"], datetime.datetime) else str(r["lot_purchase_date"])
                writer.writerow([
                    sell_date_str,
                    f"{r['sell_price']:.2f}",
                    f"{r['sell_qty']:.6f}",
                    purchase_date_str,
                    f"{r['lot_purchase_price']:.2f}",
                    f"{r['realized_pnl_usd']:.2f}",
                    r["holding_period_days"],
                    r["order_id"]
                ])
