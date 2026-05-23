import logging
from typing import Dict, Any, Tuple, Optional
from src.config import settings

logger = logging.getLogger("grid_agent")

class GridEngine:
    """
    Calculates adaptive buy/sell grid levels and order sizing parameters.
    """
    def __init__(self):
        # Load constraints from settings
        self.reserve_floor = settings.reserve_floor
        self.min_profit_threshold = settings.min_profit_threshold
        self.trading_floor_pct = settings.trading_floor

    def calculate_grid_spacing(self, sigma_ann: float) -> float:
        """
        Determines grid interval width based on 30-day annualized realized volatility.
        """
        if sigma_ann < 0.40:
            return 0.015  # 1.5% spacing
        elif sigma_ann <= 0.80:
            return 0.040  # 4.0% spacing
        else:
            return 0.080  # 8.0% spacing

    def calculate_buy_size(
        self, 
        current_price: float, 
        a_range: float, 
        remaining_reserve: float, 
        total_portfolio_value_usdt: float,
        regime: int
    ) -> float:
        """
        Calculates buy size in USDT based on drawdown from peak (A_range) and regime multiplier.
        """
        if a_range <= 0:
            return 0.0

        # Calculate drawdown from range peak
        drawdown = (a_range - current_price) / a_range
        
        # Base deployment table (percentage of remaining reserve)
        base_deploy_pct = 0.0
        if drawdown >= 0.25:
            base_deploy_pct = 0.40
        elif drawdown >= 0.15:
            base_deploy_pct = 0.30
        elif drawdown >= 0.10:
            base_deploy_pct = 0.20
        elif drawdown >= 0.06:
            base_deploy_pct = 0.10
        elif drawdown >= 0.03:
            base_deploy_pct = 0.05

        # Regime multiplier selection
        # 0: Panic Dump, 1: Sideways, 2: Bull Trend, 3: Blowoff Top, 4: Bear Market
        regime_multipliers = {
            0: 1.5,   # Panic dump
            1: 1.0,   # Sideways
            2: 0.8,   # Bull trend
            3: 0.0,   # Blowoff top (disabled)
            4: 0.4    # Bear trend
        }
        multiplier = regime_multipliers.get(regime, 1.0)

        effective_deploy_usdt = remaining_reserve * base_deploy_pct * multiplier
        
        # Invariant checks: cannot deploy if reserve falls below reserve_floor
        # reserve_floor is percentage of total portfolio value
        reserve_floor_usdt = total_portfolio_value_usdt * self.reserve_floor
        if remaining_reserve - effective_deploy_usdt < reserve_floor_usdt:
            effective_deploy_usdt = max(0.0, remaining_reserve - reserve_floor_usdt)

        return effective_deploy_usdt

    def calculate_sell_size(
        self,
        current_price: float,
        local_low: float,
        trading_btc_qty: float,
        total_portfolio_value_btc: float,
        avg_cost: float,
        regime: int
    ) -> float:
        """
        Calculates sell size in BTC based on rebound from local low, subject to sell gating and trading floor limits.
        """
        if local_low <= 0 or trading_btc_qty <= 0:
            return 0.0

        # 1. Sell Gating Check: Price must clear cost basis + minimum profit margin
        required_sell_price = avg_cost * (1.0 + self.min_profit_threshold)
        if current_price < required_sell_price:
            logger.debug(f"Sell order suppressed: price {current_price:.2f} < cost threshold {required_sell_price:.2f}")
            return 0.0

        # Calculate rebound from local low
        rebound = (current_price - local_low) / local_low
        
        # Base sell table (percentage of hot trading BTC)
        base_sell_pct = 0.0
        if rebound >= 0.12:
            base_sell_pct = 0.30
        elif rebound >= 0.08:
            base_sell_pct = 0.20
        elif rebound >= 0.04:
            base_sell_pct = 0.10

        # Regime multipliers for selling
        # 0: Panic Dump, 1: Sideways, 2: Bull Trend, 3: Blowoff Top, 4: Bear Market
        sell_multipliers = {
            0: 0.0,   # Panic dump (no sells)
            1: 1.0,   # Sideways
            2: 0.3,   # Bull trend (gồng lãi)
            3: 1.5,   # Blowoff top (chốt lãi mạnh)
            4: 0.8    # Bear trend
        }
        multiplier = sell_multipliers.get(regime, 1.0)
        
        effective_sell_btc = trading_btc_qty * base_sell_pct * multiplier

        # Ensure trading_btc_qty after sell is >= trading_floor (as % of total portfolio value in BTC)
        trading_floor_btc = total_portfolio_value_btc * self.trading_floor_pct
        if trading_btc_qty - effective_sell_btc < trading_floor_btc:
            effective_sell_btc = max(0.0, trading_btc_qty - trading_floor_btc)

        return effective_sell_btc
