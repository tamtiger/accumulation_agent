import pytest
from src.grid.engine import GridEngine

def test_grid_spacing_by_volatility():
    engine = GridEngine()
    
    # Low volatility (<40%) -> 1.5%
    assert engine.calculate_grid_spacing(0.25) == 0.015
    # Medium volatility (40%-80%) -> 4.0%
    assert engine.calculate_grid_spacing(0.50) == 0.040
    # High volatility (>80%) -> 8.0%
    assert engine.calculate_grid_spacing(0.90) == 0.080

def test_grid_buy_sizing():
    engine = GridEngine()
    
    # State values
    total_val = 100000.0
    reserve = 30000.0
    
    # 1. 2% drawdown (below 3% minimum) -> deploy 0
    size = engine.calculate_buy_size(
        current_price=9800.0,
        a_range=10000.0,
        remaining_reserve=reserve,
        total_portfolio_value_usdt=total_val,
        regime=1
    )
    assert size == 0.0

    # 2. 5% drawdown (drawdown >= 3% and < 6%) -> deploy 5% of reserve
    # regime = 1 (Sideways multiplier = 1.0)
    size = engine.calculate_buy_size(
        current_price=9600.0,
        a_range=10000.0,
        remaining_reserve=reserve,
        total_portfolio_value_usdt=total_val,
        regime=1
    )
    assert size == 30000.0 * 0.05 * 1.0  # 1,500

    # 3. 12% drawdown (drawdown >= 10% and < 15%) -> deploy 20% of reserve
    # regime = 0 (Panic Dump multiplier = 1.5)
    size = engine.calculate_buy_size(
        current_price=8800.0,
        a_range=10000.0,
        remaining_reserve=reserve,
        total_portfolio_value_usdt=total_val,
        regime=0
    )
    assert size == 30000.0 * 0.20 * 1.5  # 9,000

    # 4. Blowoff Top (regime = 3) -> deploy 0
    size = engine.calculate_buy_size(
        current_price=8800.0,
        a_range=10000.0,
        remaining_reserve=reserve,
        total_portfolio_value_usdt=total_val,
        regime=3
    )
    assert size == 0.0

def test_grid_sell_sizing():
    engine = GridEngine()
    
    # Gating parameters
    avg_cost = 40000.0
    trading_btc = 1.0
    total_btc = 2.0
    
    # 1. Price below cost gating threshold -> 0 size
    size = engine.calculate_sell_size(
        current_price=39000.0,
        local_low=38000.0,
        trading_btc_qty=trading_btc,
        total_portfolio_value_btc=total_btc,
        avg_cost_fifo_lot=avg_cost,
        regime=1
    )
    assert size == 0.0

    # 2. Rebound 2% (below 4% min) -> 0 size
    size = engine.calculate_sell_size(
        current_price=41000.0,
        local_low=40200.0,
        trading_btc_qty=trading_btc,
        total_portfolio_value_btc=total_btc,
        avg_cost_fifo_lot=avg_cost,
        regime=1
    )
    assert size == 0.0

    # 3. Rebound 5% (>=4% and <8%), price > avg_cost -> Sell 10% trading_btc
    # regime = 1 (Sideways multiplier = 1.0)
    size = engine.calculate_sell_size(
        current_price=42000.0,
        local_low=40000.0,
        trading_btc_qty=trading_btc,
        total_portfolio_value_btc=total_btc,
        avg_cost_fifo_lot=avg_cost,
        regime=1
    )
    assert abs(size - 0.10) < 1e-7

    # 4. Panic Dump (regime = 0) -> no sells
    size = engine.calculate_sell_size(
        current_price=42000.0,
        local_low=40000.0,
        trading_btc_qty=trading_btc,
        total_portfolio_value_btc=total_btc,
        avg_cost_fifo_lot=avg_cost,
        regime=0
    )
    assert size == 0.0
