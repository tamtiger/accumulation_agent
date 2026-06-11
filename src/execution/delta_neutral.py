import os
import json
import datetime
from typing import Dict, Any, List, Optional
from src.utils.logging import get_agent_logger

logger = get_agent_logger("delta_neutral")

class DeltaNeutralManager:
    """
    Manages the optional Delta-Neutral sleeve.
    Opens equal Spot Long + Perp Short positions to harvest positive funding rates.
    Monitors basis spread divergence and perp liquidation boundaries.
    """
    def __init__(self, ccxt_exchange: Any, max_allocation_pct: float = 0.20):
        self.exchange = ccxt_exchange
        self.max_allocation_pct = max_allocation_pct
        self.ledger_file = "data/delta_neutral_ledger.json"
        
        # State variables
        self.spot_qty = 0.0
        self.perp_qty = 0.0 # positive represents short quantity
        self.entry_price = 0.0
        self.entry_basis = 0.0
        self.accumulated_funding_usdt = 0.0
        self.is_active = False
        
        self.load_ledger()

    def load_ledger(self) -> None:
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r") as f:
                    data = json.load(f)
                    self.spot_qty = data.get("spot_qty", 0.0)
                    self.perp_qty = data.get("perp_qty", 0.0)
                    self.entry_price = data.get("entry_price", 0.0)
                    self.entry_basis = data.get("entry_basis", 0.0)
                    self.accumulated_funding_usdt = data.get("accumulated_funding", 0.0)
                    self.is_active = data.get("is_active", False)
            except Exception as e:
                logger.error(f"Failed to load delta neutral ledger: {e}")

    def save_ledger(self) -> None:
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        data = {
            "spot_qty": self.spot_qty,
            "perp_qty": self.perp_qty,
            "entry_price": self.entry_price,
            "entry_basis": self.entry_basis,
            "accumulated_funding": self.accumulated_funding_usdt,
            "is_active": self.is_active,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            with open(self.ledger_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save delta neutral ledger: {e}")

    def execute_tick(
        self,
        spot_price: float,
        perp_price: float,
        funding_rate: float,
        total_portfolio_val_usdt: float
    ) -> List[Dict[str, Any]]:
        """
        Evaluates funding rate and risk parameters. Generates trade orders.
        """
        proposed_orders: List[Dict[str, Any]] = []
        basis = perp_price - spot_price
        
        # 1. Risk Check: Basis Divergence or Liquidation Boundary
        risk_triggered = self.check_risk(spot_price, perp_price)
        if risk_triggered and self.is_active:
            logger.warning("Emergency risk signal triggered in Delta-Neutral sleeve. Closing positions...")
            proposed_orders.extend(self._propose_close(spot_price, perp_price))
            return proposed_orders

        # 2. Funding Harvesting Logic
        # Open condition: perp funding > 0.05% per 8h (0.0005) sustained
        if funding_rate > 0.0005 and not self.is_active:
            # Open equal Spot Long and Perp Short using max_allocation_pct (max 20% of portfolio)
            allocation_usdt = total_portfolio_val_usdt * self.max_allocation_pct
            qty = allocation_usdt / spot_price
            
            logger.info(f"High funding rate detected ({funding_rate*100:.4f}%). Opening Delta-Neutral sleeve with {qty:.4f} BTC...")
            
            # Orders: Spot Buy + Perp Short
            proposed_orders.append({
                "market": "spot",
                "side": "buy",
                "qty": qty,
                "price": spot_price
            })
            proposed_orders.append({
                "market": "perp",
                "side": "sell", # Perp short
                "qty": qty,
                "price": perp_price
            })
            
            self.spot_qty = qty
            self.perp_qty = qty
            self.entry_price = spot_price
            self.entry_basis = basis
            self.is_active = True
            self.save_ledger()

        # Close condition: funding rate drops below 0.01% (0.0001)
        elif funding_rate < 0.0001 and self.is_active:
            logger.info(f"Funding rate dropped below threshold ({funding_rate*100:.4f}%). Closing Delta-Neutral sleeve...")
            proposed_orders.extend(self._propose_close(spot_price, perp_price))

        # 3. Simulate Funding Collection if Active
        if self.is_active:
            # Collect funding: payment = perp_qty * spot_price * funding_rate
            # (Assumes standard 8h funding payout interval simplified per tick)
            funding_payment = self.perp_qty * spot_price * funding_rate
            self.accumulated_funding_usdt += funding_payment
            self.save_ledger()

        return proposed_orders

    def check_risk(self, spot_price: float, perp_price: float) -> bool:
        """
        Checks basis risk and perp liquidation boundaries.
        Returns True if safety bounds are violated.
        """
        if not self.is_active:
            return False

        # Basis risk check: Perp premium over Spot should remain stable.
        # Divergence: If Spot rises significantly above Perp (heavy backwardation), spread turns negative.
        basis_spread = (perp_price - spot_price) / spot_price
        # If basis spread drops below -2% (divergence)
        if basis_spread < -0.02:
            logger.error(f"Basis spread divergence detected: {basis_spread*100:.2f}%.")
            return True

        # Liquidation boundary check for Perp Short:
        # Assuming 5x leverage on Perp Short sleeve, liquidation price is roughly entry_price * 1.20
        # Check distance to liquidation
        liquidation_price = self.entry_price * 1.20
        distance_to_liq = (liquidation_price - perp_price) / perp_price
        # If price is within 5% of liquidation
        if distance_to_liq < 0.05:
            logger.critical(f"Perp Short is close to liquidation! Distance: {distance_to_liq*100:.2f}%.")
            return True

        return False

    def _propose_close(self, spot_price: float, perp_price: float) -> List[Dict[str, Any]]:
        orders = [
            {
                "market": "spot",
                "side": "sell",
                "qty": self.spot_qty,
                "price": spot_price
            },
            {
                "market": "perp",
                "side": "buy", # Cover perp short
                "qty": self.perp_qty,
                "price": perp_price
            }
        ]
        # Reset state
        self.spot_qty = 0.0
        self.perp_qty = 0.0
        self.entry_price = 0.0
        self.entry_basis = 0.0
        self.is_active = False
        self.save_ledger()
        return orders
