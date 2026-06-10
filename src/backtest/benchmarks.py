import pandas as pd
from typing import Dict, Any
from unittest.mock import patch
from src.backtest.harness import BacktestHarness
from src.grid.engine import GridEngine

def run_passive_hodl(df_data: pd.DataFrame, initial_usdt: float, initial_core_btc: float) -> float:
    """
    Simulates a passive HODL strategy where all cash is converted to BTC on day 0.
    Returns final portfolio value in BTC.
    """
    if df_data.empty:
        return initial_core_btc
    start_price = float(df_data.iloc[0]["close"])
    final_price = float(df_data.iloc[-1]["close"])
    total_btc = initial_core_btc + (initial_usdt / start_price)
    return total_btc

def run_weekly_dca(
    df_data: pd.DataFrame, 
    initial_usdt: float, 
    initial_core_btc: float, 
    taker_fee: float = 0.0010
) -> float:
    """
    Simulates a weekly DCA strategy. Distributes the initial USDT reserve equally
    over the weeks of the backtest duration.
    Returns final portfolio value in BTC.
    """
    if df_data.empty:
        return initial_core_btc
        
    total_ticks = len(df_data)
    weekly_interval = 168  # 168 hours in a week
    num_weeks = max(1, total_ticks // weekly_interval)
    weekly_usdt = initial_usdt / num_weeks
    
    usdt_balance = initial_usdt
    btc_balance = initial_core_btc
    final_price = float(df_data.iloc[-1]["close"])
    
    for idx in range(0, total_ticks, weekly_interval):
        if usdt_balance < weekly_usdt:
            deploy_usdt = usdt_balance
        else:
            deploy_usdt = weekly_usdt
            
        if deploy_usdt <= 0:
            break
            
        price = float(df_data.iloc[idx]["close"])
        fee = deploy_usdt * taker_fee
        bought_btc = (deploy_usdt - fee) / price
        btc_balance += bought_btc
        usdt_balance -= deploy_usdt
        
    return btc_balance + (usdt_balance / final_price)

def run_core_plus_weekly_dca(
    df_data: pd.DataFrame,
    initial_usdt: float,
    initial_core_btc: float,
    taker_fee: float = 0.0010
) -> float:
    """
    Simulates Core BTC + Weekly DCA (no active swing sleeve).
    Splits initial_usdt: 70% converted to Core BTC on Day 1, 30% deployed weekly.
    Returns final portfolio value in BTC.
    """
    if df_data.empty:
        return initial_core_btc
        
    start_price = float(df_data.iloc[0]["close"])
    core_initial_usdt = initial_usdt * 0.70
    dca_initial_usdt = initial_usdt * 0.30
    
    # Day 1 Buy
    fee_core = core_initial_usdt * taker_fee
    core_btc = initial_core_btc + (core_initial_usdt - fee_core) / start_price
    
    # Weekly DCA of the remaining 30%
    return run_weekly_dca(df_data, dca_initial_usdt, core_btc, taker_fee)

class FixedGridEngine(GridEngine):
    """
    Overridden GridEngine forcing 5% spacing and constant multipliers (1.0).
    """
    def calculate_grid_spacing(self, sigma_ann: float) -> float:
        return 0.05  # Fixed 5% grid spacing

    def calculate_buy_size(
        self, 
        current_price: float, 
        a_range: float, 
        remaining_reserve: float, 
        total_portfolio_value_usdt: float,
        regime: int
    ) -> float:
        # Override regime to always be 1 (Sideways / Multiplier = 1.0)
        return super().calculate_buy_size(
            current_price=current_price,
            a_range=a_range,
            remaining_reserve=remaining_reserve,
            total_portfolio_value_usdt=total_portfolio_value_usdt,
            regime=1
        )

    def calculate_sell_size(
        self,
        current_price: float,
        local_low: float,
        trading_btc_qty: float,
        total_portfolio_value_btc: float,
        avg_cost_fifo_lot: float,
        regime: int
    ) -> float:
        # Override regime to always be 1 (Sideways / Multiplier = 1.0)
        return super().calculate_sell_size(
            current_price=current_price,
            local_low=local_low,
            trading_btc_qty=trading_btc_qty,
            total_portfolio_value_btc=total_portfolio_value_btc,
            avg_cost_fifo_lot=avg_cost_fifo_lot,
            regime=1
        )

def run_fixed_grid_backtest(
    df_data: pd.DataFrame,
    initial_usdt: float = 100000.0,
    initial_core_btc: float = 0.0,
    tax_rate: float = 0.20,
    maker_fee: float = 0.0002,
    taker_fee: float = 0.0010,
    slippage: float = 0.0005
) -> Dict[str, Any]:
    """
    Runs the backtest harness using the FixedGridEngine (static 5% grid, 1.0 multipliers).
    """
    harness = BacktestHarness(
        initial_usdt=initial_usdt,
        initial_core_btc=initial_core_btc,
        tax_rate=tax_rate,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        slippage=slippage
    )
    
    # Inject FixedGridEngine
    harness.orchestrator.grid_engine = FixedGridEngine()
    
    # Precompute features to mock database queries
    df_features = harness.orchestrator.features_engine.calculate_anchors_and_features(df_data)
    
    def mock_compute_latest_features(limit=500):
        # Retrieve row corresponding to the current state of backtest
        # The number of records in binance_ohlcv table tells us the current tick index
        conn = None
        try:
            from src.utils.db import get_connection, release_connection
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM binance_ohlcv")
                count = cur.fetchone()[0]
                if count == 0:
                    return None
                row_idx = min(count - 1, len(df_features) - 1)
                row = df_features.iloc[row_idx]
                return row.to_dict()
        except Exception:
            return None
        finally:
            if conn:
                release_connection(conn)
                
    harness.orchestrator.features_engine.compute_latest_features = mock_compute_latest_features
    
    results = harness.run(df_data)
    return results
