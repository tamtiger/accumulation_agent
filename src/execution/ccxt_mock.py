import time
import uuid
import random
import datetime
from typing import Dict, Any, Optional

class BinanceMock:
    """
    Mock implementation of ccxt.binance for simulation, backtesting, and validation.
    """
    def __init__(self, reserve_usdt: float = 50000.0, trading_btc: float = 0.5):
        self.reserve_usdt = reserve_usdt
        self.trading_btc = trading_btc
        self.orders: Dict[str, Dict[str, Any]] = {}
        
        # Perpetual mock tracking
        self.perp_position_qty = 0.0
        self.perp_position_entry = 0.0
        
        # Fee model parameters
        self.maker_fee = 0.0002  # 0.02%
        self.taker_fee = 0.0010  # 0.10%
        self.slippage_mean = 0.0005  # 0.05% default mean slippage

    def fetch_balance(self) -> Dict[str, Any]:
        """
        Mimics CCXT fetch_balance output schema.
        """
        return {
            "free": {
                "USDT": self.reserve_usdt,
                "BTC": self.trading_btc
            },
            "total": {
                "USDT": self.reserve_usdt,
                "BTC": self.trading_btc
            },
            "USDT": {
                "free": self.reserve_usdt,
                "used": 0.0,
                "total": self.reserve_usdt
            },
            "BTC": {
                "free": self.trading_btc,
                "used": 0.0,
                "total": self.trading_btc
            }
        }

    def create_order(
        self,
        symbol: str,
        type_val: Optional[str] = None,
        side: str = "buy",
        amount: float = 0.0,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
        type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mimics CCXT create_order output schema, updating internal mock balances and modeling slippage & fees.
        """
        order_type = type_val or type or "limit"
        order_id = f"mock-order-{uuid.uuid4()}"
        
        # Calculate execution price with simulated slippage
        # Buy: slippage increases buy price. Sell: slippage decreases sell price.
        # Ensure slippage is positive
        slippage = abs(random.gauss(self.slippage_mean, 0.0001))
        
        limit_price = price if price is not None else 50000.0
        if side == "buy":
            executed_price = limit_price * (1.0 + slippage)
        else:
            executed_price = limit_price * (1.0 - slippage)

        cost = amount * executed_price
        
        # Determine fee based on order type (limit -> maker, market -> taker)
        fee_rate = self.maker_fee if order_type.lower() == "limit" else self.taker_fee
        fee_cost = cost * fee_rate
        
        # Check if perpetual market symbol
        is_perp = ":" in symbol or symbol.endswith("USDT:USDT")
        
        if is_perp:
            # Perpetual execution flow
            if side == "sell":  # Open perp short
                if self.perp_position_qty == 0.0:
                    self.perp_position_entry = executed_price
                else:
                    self.perp_position_entry = (
                        (self.perp_position_entry * self.perp_position_qty + executed_price * amount) /
                        (self.perp_position_qty + amount)
                    )
                self.perp_position_qty += amount
                self.reserve_usdt -= fee_cost
            else:  # Close/Cover perp short
                if self.perp_position_qty > 0.0:
                    closed_qty = min(amount, self.perp_position_qty)
                    # short pnl = qty * (entry_price - execution_price)
                    pnl = closed_qty * (self.perp_position_entry - executed_price)
                    self.reserve_usdt += (pnl - fee_cost)
                    self.perp_position_qty -= closed_qty
                    if self.perp_position_qty == 0.0:
                        self.perp_position_entry = 0.0
                else:
                    self.reserve_usdt -= fee_cost
        else:
            # Spot execution flow
            if side == "buy":
                total_cost = cost + fee_cost
                if total_cost > self.reserve_usdt:
                    # Adjust size to max possible if not enough reserve (safety cap)
                    amount = (self.reserve_usdt * 0.99) / (executed_price * (1.0 + fee_rate))
                    cost = amount * executed_price
                    fee_cost = cost * fee_rate
                    total_cost = cost + fee_cost
                    
                self.reserve_usdt -= total_cost
                self.trading_btc += amount
            else:
                if amount > self.trading_btc:
                    amount = self.trading_btc
                    cost = amount * executed_price
                    fee_cost = cost * fee_rate
    
                self.reserve_usdt += (cost - fee_cost)
                self.trading_btc -= amount

        order = {
            "id": order_id,
            "clientOrderId": order_id,
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "lastTradeTimestamp": int(time.time() * 1000),
            "status": "closed",
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "price": limit_price,
            "amount": amount,
            "cost": cost,
            "average": executed_price,
            "filled": amount,
            "remaining": 0.0,
            "fee": {
                "cost": fee_cost,
                "currency": "USDT"
            },
            "info": {
                "slippage": slippage
            }
        }
        
        self.orders[order_id] = order
        return order
