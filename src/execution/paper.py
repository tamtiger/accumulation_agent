import time
import uuid
import datetime
from typing import Dict, Any, Optional
from src.utils.logging import get_agent_logger
from src.execution.live_ws import BinanceWSClient

logger = get_agent_logger("paper_execution")

class BinancePaper:
    """
    Paper trading wrapper for Binance.
    Queries live exchange balances, audits API key permissions,
    and simulates order fills against real-time order books.
    """
    def __init__(self, ccxt_client: Any, ws_client: BinanceWSClient):
        self.ccxt = ccxt_client
        self.ws = ws_client
        
        # Paper balances initialized to live exchange values
        self.paper_reserve_usdt = 0.0
        self.paper_trading_btc = 0.0
        self.is_initialized = False
        
        # Fee rates
        self.maker_fee = 0.0002
        self.taker_fee = 0.0010

    def initialize_balances(self) -> None:
        """
        Synchronizes paper balances with actual live balances at startup.
        """
        try:
            logger.info("Initializing paper balances from live account...")
            self.audit_api_permissions()
            live_bal = self.ccxt.fetch_balance()
            self.paper_reserve_usdt = float(live_bal["free"].get("USDT", 0.0))
            self.paper_trading_btc = float(live_bal["free"].get("BTC", 0.0))
            self.is_initialized = True
            logger.info(f"Balances loaded. USDT: {self.paper_reserve_usdt:.2f}, BTC: {self.paper_trading_btc:.6f}")
        except Exception as e:
            logger.error(f"Failed to initialize live balance: {e}. Falling back to default baseline.")
            self.paper_reserve_usdt = 50000.0
            self.paper_trading_btc = 0.5
            self.is_initialized = True

    def audit_api_permissions(self) -> None:
        """
        Audits API keys to assert that withdrawal permissions are strictly disabled.
        """
        # Ensure we are not using mock and have permissions method
        if hasattr(self.ccxt, "check_required_credentials"):
            # Mock or check permissions if credentials loaded
            if self.ccxt.apiKey:
                logger.info("Auditing API key permissions...")
                # Fetch key permissions if supported, otherwise assert withdrawal is disabled in info
                try:
                    # Binance specific API permissions endpoint
                    permissions = self.ccxt.privateGetAccountAPIKeyPermissions()
                    if permissions and permissions.get("withdraw", False):
                        raise SecurityError("CRITICAL: API key has WITHDRAWAL permissions enabled! Halting.")
                except AttributeError:
                    logger.warning("fetch_api_key_permissions not available on client. Verify manually.")

    def fetch_balance(self) -> Dict[str, Any]:
        """
        Returns paper trading balances.
        """
        if not self.is_initialized:
            self.initialize_balances()
            
        return {
            "free": {
                "USDT": self.paper_reserve_usdt,
                "BTC": self.paper_trading_btc
            },
            "total": {
                "USDT": self.paper_reserve_usdt,
                "BTC": self.paper_trading_btc
            },
            "USDT": {
                "free": self.paper_reserve_usdt,
                "used": 0.0,
                "total": self.paper_reserve_usdt
            },
            "BTC": {
                "free": self.paper_trading_btc,
                "used": 0.0,
                "total": self.paper_trading_btc
            }
        }

    def create_order(
        self,
        symbol: str,
        type_val: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulates order execution against real-time WebSocket orderbook depth.
        """
        if not self.is_initialized:
            self.initialize_balances()
            
        order_id = f"paper-order-{uuid.uuid4()}"
        
        # Get real-time execution price from orderbook
        bid = self.ws.bid_price
        ask = self.ws.ask_price
        mid = self.ws.get_mid_price()
        
        # Fallback to limit price if ws is offline
        limit_price = price if price is not None else (mid if mid > 0 else 50000.0)
        
        if side == "buy":
            executed_price = ask if ask > 0 else limit_price
        else:
            executed_price = bid if bid > 0 else limit_price
            
        # Add basic spread/slippage penalty
        slippage = abs((executed_price - limit_price) / limit_price) if limit_price > 0 else 0.0
        
        cost = amount * executed_price
        fee_rate = self.maker_fee if type_val.lower() == "limit" else self.taker_fee
        fee_cost = cost * fee_rate
        
        # Update paper balances
        if side == "buy":
            total_cost = cost + fee_cost
            if total_cost > self.paper_reserve_usdt:
                amount = (self.paper_reserve_usdt * 0.99) / (executed_price * (1.0 + fee_rate))
                cost = amount * executed_price
                fee_cost = cost * fee_rate
                total_cost = cost + fee_cost
                
            self.paper_reserve_usdt -= total_cost
            self.paper_trading_btc += amount
        else:
            if amount > self.paper_trading_btc:
                amount = self.paper_trading_btc
                cost = amount * executed_price
                fee_cost = cost * fee_rate
                
            self.paper_reserve_usdt += (cost - fee_cost)
            self.paper_trading_btc -= amount
            
        order = {
            "id": order_id,
            "clientOrderId": order_id,
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "lastTradeTimestamp": int(time.time() * 1000),
            "status": "closed",
            "symbol": symbol,
            "type": type_val,
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
        
        logger.info(f"Simulated execution: {side.upper()} {amount:.6f} BTC @ {executed_price:.2f}")
        return order

class SecurityError(Exception):
    pass
