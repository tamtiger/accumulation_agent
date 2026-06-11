import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List

class ABASGymEnv:
    """
    Custom Gym-like environment for ABAS v2 reinforcement learning optimization.
    Exposes state vectors, parses actions, simulates portfolio updates, and returns rewards.
    """
    def __init__(self, df_features: pd.DataFrame, initial_reserve_usdt: float = 100000.0):
        self.df = df_features.reset_index(drop=True)
        self.initial_reserve_usdt = initial_reserve_usdt
        
        # State dimension and action dimension
        self.state_dim = 21 # Matching state representation vector length
        self.action_dim = 4 # [grid_spacing_mult, reserve_deploy_mult, sell_ratio_mult, profit_threshold_mult]
        
        self.current_idx = 0
        self.n_steps = len(self.df)
        
        # Portfolio variables
        self.core_btc = 0.0
        self.trading_btc = 0.0
        self.reserve_usdt = initial_reserve_usdt
        
        self.initial_hodl_btc = 0.0
        self.last_portfolio_value_usdt = initial_reserve_usdt
        self.peak_portfolio_value_usdt = initial_reserve_usdt
        
        # FIFO cost tracking
        self.buy_lots: List[Dict[str, float]] = [] # list of {"qty": q, "price": p}

    def reset(self) -> np.ndarray:
        self.current_idx = 30 # Start after feature warmup
        self.core_btc = 0.0
        self.trading_btc = 0.0
        self.reserve_usdt = self.initial_reserve_usdt
        
        start_price = float(self.df.loc[self.current_idx, "close"])
        self.initial_hodl_btc = self.initial_reserve_usdt / start_price
        self.last_portfolio_value_usdt = self.initial_reserve_usdt
        self.peak_portfolio_value_usdt = self.initial_reserve_usdt
        self.buy_lots = []
        
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        row = self.df.iloc[self.current_idx]
        price = float(row["close"])
        
        # Calculate features
        ret_1h = float(row.get("returns", 0.0))
        ret_24h = float(row.get("returns_24h", ret_1h * 24))
        ret_7d = float(row.get("returns_7d", ret_1h * 168))
        
        vol_short = float(row.get("vol_short", 0.15))
        vol_long = float(row.get("vol_long", 0.25))
        atr_norm = float(row.get("atr_normalized", 0.02))
        
        ema20_slope = float(row.get("ema20_slope", 0.0))
        ema200_slope = float(row.get("ema200_slope", 0.0))
        price_vs_ema200 = float(row.get("price_vs_ema200", 0.0))
        
        funding = float(row.get("funding_rate", 0.0001))
        oi_delta = float(row.get("oi_delta", 0.0))
        liq_intensity = float(row.get("liquidations", 0.0))
        
        # Regime representation
        regime = int(row.get("regime", 1))
        regime_onehot = np.zeros(5)
        regime_onehot[regime] = 1.0
        
        # Portfolio values
        total_btc = self.core_btc + self.trading_btc
        total_val_usdt = self.reserve_usdt + total_btc * price
        
        core_btc_ratio = (self.core_btc * price) / total_val_usdt if total_val_usdt > 0 else 0.0
        trading_btc_ratio = (self.trading_btc * price) / total_val_usdt if total_val_usdt > 0 else 0.0
        reserve_ratio = self.reserve_usdt / total_val_usdt if total_val_usdt > 0 else 0.0
        
        # Cost basis distance (FIFO lot head)
        if len(self.buy_lots) > 0:
            avg_cost = self.buy_lots[0]["price"]
            cost_dist = (price - avg_cost) / avg_cost
        else:
            cost_dist = 0.0
            
        unrealized_pnl = total_btc * price - sum(lot["qty"] * lot["price"] for lot in self.buy_lots)
        unrealized_pnl_btc = unrealized_pnl / price if price > 0 else 0.0
        
        # Capacity and headroom
        reserve_headroom = max(0.0, reserve_ratio - 0.15) # reserve_floor = 15%
        
        state = [
            price, ret_1h, ret_24h, ret_7d, vol_short, vol_long, atr_norm,
            ema20_slope, ema200_slope, price_vs_ema200, funding, oi_delta, liq_intensity,
            regime, 0.95, # confidence default 0.95
            core_btc_ratio, trading_btc_ratio, reserve_ratio,
            cost_dist, unrealized_pnl_btc, reserve_headroom
        ]
        return np.array(state, dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Executes one step in the environment.
        action: [grid_spacing_mult, reserve_deploy_mult, sell_ratio_mult, profit_threshold_mult]
        Returns (next_state, reward, done, info)
        """
        # Parse action multipliers (bounded between 0.5 and 1.5)
        action = np.clip(action, 0.5, 1.5)
        grid_spacing_mult = action[0]
        reserve_deploy_mult = action[1]
        sell_ratio_mult = action[2]
        profit_threshold_mult = action[3]
        
        row = self.df.iloc[self.current_idx]
        price = float(row["close"])
        vol = float(row.get("sigma_ann", 0.30))
        int(row.get("regime", 1))
        
        # Calculate portfolio value before trading
        total_btc_before = self.core_btc + self.trading_btc
        portfolio_val_before_usdt = self.reserve_usdt + total_btc_before * price
        
        trade_count = 0
        fee_cost = 0.0
        
        # Simulating Buy Order
        # Normal base deployment is 5% of reserve when price falls
        # Grid spacing = vol * 0.1 * grid_spacing_mult
        spacing = vol * 0.1 * grid_spacing_mult
        a_range = float(row.get("A_range", price * 1.05))
        drawdown = (a_range - price) / a_range
        
        # Determine if we should buy
        if drawdown > spacing and self.reserve_usdt > portfolio_val_before_usdt * 0.15: # reserve_floor = 15%
            buy_budget = self.reserve_usdt * 0.05 * reserve_deploy_mult
            # Cap buy size
            buy_budget = min(buy_budget, self.reserve_usdt)
            if buy_budget >= 10.0:
                qty_bought = buy_budget / price
                fee = buy_budget * 0.0010 # taker fee = 0.1%
                self.reserve_usdt -= (buy_budget + fee)
                self.trading_btc += qty_bought
                self.buy_lots.append({"qty": qty_bought, "price": price})
                trade_count += 1
                fee_cost += fee
                
        # Simulating Sell Order
        # Normal base sell is 10% of trading BTC if price is above cost
        min_profit_threshold = 0.01 * profit_threshold_mult
        if len(self.buy_lots) > 0 and self.trading_btc > 0.0:
            head_lot = self.buy_lots[0]
            if price >= head_lot["price"] * (1.0 + min_profit_threshold):
                qty_to_sell = self.trading_btc * 0.10 * sell_ratio_mult
                qty_to_sell = min(qty_to_sell, self.trading_btc)
                if qty_to_sell > 0.0001:
                    sell_value = qty_to_sell * price
                    fee = sell_value * 0.0010
                    self.reserve_usdt += (sell_value - fee)
                    self.trading_btc -= qty_to_sell
                    
                    # Consume lots
                    remaining_to_sell = qty_to_sell
                    while remaining_to_sell > 0 and len(self.buy_lots) > 0:
                        lot = self.buy_lots[0]
                        if lot["qty"] <= remaining_to_sell:
                            remaining_to_sell -= lot["qty"]
                            self.buy_lots.pop(0)
                        else:
                            lot["qty"] -= remaining_to_sell
                            remaining_to_sell = 0.0
                            
                    trade_count += 1
                    fee_cost += fee

        # Strategic Core Promotion Sweep
        trading_target = 0.20 * (self.reserve_usdt + (self.core_btc + self.trading_btc) * price) / price
        if self.trading_btc > trading_target * 1.3:
            excess = self.trading_btc - trading_target
            self.core_btc += excess
            self.trading_btc -= excess
            
        # 4. Step Environment Index
        self.current_idx += 1
        done = (self.current_idx >= self.n_steps - 1)
        
        # Calculate new portfolio values
        row_next = self.df.iloc[self.current_idx]
        price_next = float(row_next["close"])
        total_btc_after = self.core_btc + self.trading_btc
        portfolio_val_after_usdt = self.reserve_usdt + total_btc_after * price_next
        
        # Keep track of peak for drawdown calculations
        if portfolio_val_after_usdt > self.peak_portfolio_value_usdt:
            self.peak_portfolio_value_usdt = portfolio_val_after_usdt
            
        # 5. Reward Calculation
        # Primary: BTC Growth
        total_btc_val_after = total_btc_after + (self.reserve_usdt / price_next)
        total_btc_val_before = total_btc_before + (self.reserve_usdt / price)
        btc_growth = (total_btc_val_after - total_btc_val_before) / total_btc_val_before if total_btc_val_before > 0 else 0.0
        
        # Drawdown Penalty
        drawdown_pct = (self.peak_portfolio_value_usdt - portfolio_val_after_usdt) / self.peak_portfolio_value_usdt
        drawdown_penalty = 0.5 * max(0.0, drawdown_pct - 0.10) # penalize drawdown > 10%
        
        # Overtrading Penalty
        overtrading_penalty = 0.01 * trade_count + (fee_cost / portfolio_val_before_usdt)
        
        # Reserve Depletion Penalty
        reserve_ratio = self.reserve_usdt / portfolio_val_after_usdt
        reserve_depletion_penalty = 1.0 * max(0.0, 0.15 - reserve_ratio) # penalize going below floor 15%
        
        # HODL Underperformance Penalty
        hodl_value_btc = self.initial_hodl_btc
        portfolio_val_btc = total_btc_after + (self.reserve_usdt / price_next)
        hodl_diff = portfolio_val_btc - hodl_value_btc
        hodl_underperformance_penalty = 2.0 * max(0.0, -hodl_diff)
        
        reward = (
            btc_growth * 100.0
            - drawdown_penalty
            - overtrading_penalty
            - reserve_depletion_penalty
            - hodl_underperformance_penalty
        )
        
        next_state = self._get_state() if not done else np.zeros(self.state_dim)
        
        info = {
            "portfolio_value_usdt": portfolio_val_after_usdt,
            "btc_growth": btc_growth,
            "drawdown": drawdown_pct,
            "trade_count": trade_count,
            "reserve_ratio": reserve_ratio
        }
        
        return next_state, float(reward), done, info
