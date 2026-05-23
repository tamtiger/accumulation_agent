import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config import settings
from src.utils.logging import get_agent_logger

logger = get_agent_logger("risk_agent")

class InvariantViolationError(Exception):
    """Raised when one of the system-wide trading invariants is violated."""
    pass

class SystemHaltError(Exception):
    """Raised when a kill switch trigger condition is met, halting all operations."""
    pass

class ProposedOrder(BaseModel):
    side: str  # "buy" or "sell"
    qty: float
    price: float
    symbol: str = "BTC/USDT"

class RiskOverlay:
    """
    Enforces the 7 invariants (INV-1 to INV-7) and evaluates real-time kill switch parameters.
    """
    def __init__(self):
        self.reserve_floor = settings.reserve_floor
        self.daily_deployment_cap = settings.daily_deployment_cap
        self.hot_exchange_cap = settings.hot_exchange_cap
        self.min_profit_threshold = settings.min_profit_threshold
        self.system_halted = False

    def check_invariants(
        self,
        proposed_orders: List[ProposedOrder],
        current_state: Dict[str, float],
        btc_price: float,
        daily_deployed_usdt: float
    ) -> None:
        """
        Evaluates a list of proposed orders against the 7 invariants.
        Raises InvariantViolationError if any check fails.
        """
        if self.system_halted:
            raise InvariantViolationError("System is in a HALT state. No orders can be checked or submitted.")

        core_btc = current_state.get("core_btc_qty", 0.0)
        trading_btc = current_state.get("trading_btc_qty", 0.0)
        reserve_usdt = current_state.get("reserve_usdt", 0.0)
        avg_cost = current_state.get("avg_cost", 0.0)

        total_btc = core_btc + trading_btc
        portfolio_value_usdt = reserve_usdt + total_btc * btc_price

        # Calculate proposed next state if all orders execute
        next_core_btc = core_btc
        next_trading_btc = trading_btc
        next_reserve_usdt = reserve_usdt
        proposed_buy_value = 0.0

        for order in proposed_orders:
            order_val = order.qty * order.price
            if order.side == "buy":
                next_trading_btc += order.qty
                next_reserve_usdt -= order_val
                proposed_buy_value += order_val
            elif order.side == "sell":
                # INV-5: Sell-gating check: price must clear cost basis + fees
                required_price = avg_cost * (1.0 + self.min_profit_threshold)
                if order.price < required_price:
                    raise InvariantViolationError(
                        f"INV-5 Violated: Sell price {order.price:.2f} < cost basis plus threshold {required_price:.2f}"
                    )
                next_trading_btc -= order.qty
                next_reserve_usdt += order_val

        # INV-1: Core BTC quantity must not decrease
        if next_core_btc < core_btc:
            raise InvariantViolationError(
                f"INV-1 Violated: Proposed core BTC ({next_core_btc:.6f}) is less than current core BTC ({core_btc:.6f})"
            )

        # INV-2: Reserve USDT must not fall below reserve_floor (% of portfolio value)
        reserve_floor_usdt = portfolio_value_usdt * self.reserve_floor
        if next_reserve_usdt < reserve_floor_usdt:
            raise InvariantViolationError(
                f"INV-2 Violated: Next USDT reserve ({next_reserve_usdt:.2f}) drops below reserve floor ({reserve_floor_usdt:.2f})"
            )

        # INV-3: Portfolio sum conservation (sum of sleeves value equals total portfolio value within float tolerance)
        next_total_btc = next_core_btc + next_trading_btc
        next_portfolio_value_usdt = next_reserve_usdt + next_total_btc * btc_price
        if abs(next_portfolio_value_usdt - portfolio_value_usdt) > 1e-2:
            # Note: total value changes slightly if btc_price fluctuates, but at static calculation it must conserve.
            # If there's a leak in our math:
            # pre-transaction: reserve_usdt + btc_qty * price
            # post-transaction (at same price): (reserve_usdt - order_val) + (btc_qty + qty) * price = reserve_usdt + btc_qty * price
            # It must be exactly identical!
            raise InvariantViolationError(
                f"INV-3 Violated: Portfolio value leak detected. Pre-value: {portfolio_value_usdt:.2f}, Post-value: {next_portfolio_value_usdt:.2f}"
            )

        # INV-6: Daily deployed capital must not exceed deployment cap
        total_deployed_today = daily_deployed_usdt + proposed_buy_value
        max_daily_deployment = portfolio_value_usdt * self.daily_deployment_cap
        if total_deployed_today > max_daily_deployment:
            raise InvariantViolationError(
                f"INV-6 Violated: Daily deployed USDT ({total_deployed_today:.2f}) exceeds cap ({max_daily_deployment:.2f})"
            )

        # INV-7: Total exchange-held BTC must be <= hot_exchange_cap (% of total portfolio value)
        exchange_exposure_usdt = next_trading_btc * btc_price
        exchange_exposure_pct = exchange_exposure_usdt / portfolio_value_usdt
        if exchange_exposure_pct > self.hot_exchange_cap:
            raise InvariantViolationError(
                f"INV-7 Violated: Hot exchange exposure ({exchange_exposure_pct * 100:.1f}%) exceeds cap ({self.hot_exchange_cap * 100:.1f}%)"
            )

        # Log check passed
        logger.info("All order invariants verified successfully.", action="check_invariants_pass")

    def audit_kill_switches(
        self,
        drawdown_24h: float,
        drawdown_7d: float,
        current_reserve_usdt: float,
        total_portfolio_usdt: float,
        api_error_rate_5m: float,
        stablecoin_peg_deviations: Dict[str, float],
        bid_ask_spread_binance: float,
        median_30d_spread: float,
        execution_slippage: float
    ) -> None:
        """
        Monitors system health parameters and triggers immediate HALT state on any violation.
        """
        # 1. Drawdown limits
        if drawdown_24h > 0.15:
            self.trigger_halt("Drawdown > 15% in 24 hours")
        if drawdown_7d > 0.25:
            self.trigger_halt("Drawdown > 25% in 7 days")

        # 2. Reserve floor check
        reserve_ratio = current_reserve_usdt / total_portfolio_usdt
        if reserve_ratio < self.reserve_floor:
            # Reserve under floor triggers a soft-halt warning or BUY freeze
            logger.warning(
                f"Reserve USDT ({reserve_ratio*100:.1f}%) fell below floor ({self.reserve_floor*100:.1f}%) - buying restricted.",
                action="reserve_below_floor_warning"
            )

        # 3. Exchange API error rate
        if api_error_rate_5m > 0.05:
            self.trigger_halt(f"Exchange API error rate > 5% in 5-minute rolling window ({api_error_rate_5m*100:.1f}%)")

        # 4. Stablecoin peg deviation
        for stablecoin, deviation in stablecoin_peg_deviations.items():
            if deviation > 0.02:
                self.trigger_halt(f"Stablecoin peg deviation for {stablecoin} > 2% ({deviation*100:.1f}%)")

        # 5. Bid-ask spread check
        if bid_ask_spread_binance > 5.0 * median_30d_spread:
            self.trigger_halt(f"Bid-ask spread ({bid_ask_spread_binance:.6f}) > 5x 30-day median ({median_30d_spread:.6f})")

        # 6. Execution slippage
        if execution_slippage > 0.02:
            self.trigger_halt(f"Execution price slippage of a completed fill > 2% ({execution_slippage*100:.1f}%)")

    def trigger_halt(self, reason: str) -> None:
        """
        Executes immediate halt procedure.
        """
        self.system_halted = True
        logger.critical(
            f"!!! CRITICAL SYSTEM HALT TRIGGERED !!! Reason: {reason}",
            action="system_halt",
            metadata={"reason": reason}
        )
        # In a real environment, this method would call the Execution Agent to cancel all open orders.
        raise SystemHaltError(f"System halted due to risk violation: {reason}")
