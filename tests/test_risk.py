import pytest
from src.risk.overlay import RiskOverlay, ProposedOrder, InvariantViolationError, SystemHaltError

def test_risk_overlay_invariants_pass():
    overlay = RiskOverlay()
    
    # Define state
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 30000.0,
        "avg_cost": 40000.0
    }
    
    # Proposed order: BUY 0.1 BTC at 50,000 (value = 5,000)
    # Total portfolio val: 30,000 + 1.2 * 50,000 = 90,000
    # Reserve floor is 15% of 90,000 = 13,500
    # Next reserve: 30,000 - 5,000 = 25,000 (which is > 13,500)
    # Daily deployed = 0. Max daily = 5% of 90,000 = 4,500?
    # Wait, 5,000 value exceeds 5% of 90,000 (4,500) daily deployment cap!
    # Let's adjust daily_deployment_cap or order size to be within cap (e.g. BUY 0.05 BTC = 2,500)
    
    orders = [
        ProposedOrder(side="buy", qty=0.05, price=50000.0)
    ]
    
    # Should pass without exceptions
    overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)

def test_risk_overlay_inv2_reserve_floor():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 15000.0,  # low reserve
        "avg_cost": 40000.0
    }
    # Total portfolio val: 15,000 + 1.2 * 50,000 = 75,000
    # Reserve floor = 15% of 75,000 = 11,250
    # Buying 0.1 BTC at 50,000 costs 5,000. Next reserve: 10,000 (below floor 11,250)
    orders = [
        ProposedOrder(side="buy", qty=0.1, price=50000.0)
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-2 Violated" in str(excinfo.value)

def test_risk_overlay_inv5_sell_gating():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 30000.0,
        "avg_cost": 50000.0
    }
    # Average cost = 50,000. min_profit_threshold = 0.375%
    # Min sell price = 50,000 * 1.00375 = 50,187.5
    # Selling at 49,000 should violate INV-5
    orders = [
        ProposedOrder(side="sell", qty=0.1, price=49000.0)
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-5 Violated" in str(excinfo.value)

def test_risk_overlay_inv5_sell_gating_fifo_head():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 30000.0,
        "avg_cost": 40000.0,             # global average is low
        "avg_cost_fifo_lot": 50000.0      # FIFO head is high cost
    }
    # FIFO head is 50,000. Min sell price = 50,000 * 1.00375 = 50,187.5
    # Selling at 49,000 should violate INV-5, even though 49,000 > 40,000 (avg_cost)
    orders = [
        ProposedOrder(side="sell", qty=0.1, price=49000.0)
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-5 Violated" in str(excinfo.value)

def test_risk_overlay_inv6_deployment_cap():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 50000.0,
        "avg_cost": 40000.0
    }
    # Total portfolio val: 50,000 + 1.2 * 50,000 = 110,000
    # daily_deployment_cap = 5% of 110,000 = 5,500
    # Trying to deploy 6,000 in buys
    orders = [
        ProposedOrder(side="buy", qty=0.12, price=50000.0) # value = 6,000
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-6 Violated" in str(excinfo.value)

def test_risk_overlay_inv7_hot_exchange_cap():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 0.1,
        "trading_btc_qty": 0.8,  # hot btc is high
        "reserve_usdt": 50000.0,
        "avg_cost": 40000.0
    }
    # Total portfolio val: 50,000 + 0.9 * 50,000 = 95,000
    # Hot exchange cap = 25% of 95,000 = 23,750
    # Current hot exchange val = 0.8 * 50,000 = 40,000 (> 23,750)
    # Checking invariants should trigger INV-7
    orders = [
        ProposedOrder(side="buy", qty=0.01, price=50000.0)
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-7 Violated" in str(excinfo.value)

def test_kill_switches():
    overlay = RiskOverlay()
    
    # Spread > 5x median spread
    with pytest.raises(SystemHaltError) as excinfo:
        overlay.audit_kill_switches(
            drawdown_24h=0.02,
            drawdown_7d=0.05,
            current_reserve_usdt=30000.0,
            total_portfolio_usdt=100000.0,
            api_error_rate_5m=0.01,
            stablecoin_peg_deviations={"USDT": 0.005},
            bid_ask_spread_binance=0.05,
            median_30d_spread=0.002,  # 0.05 > 25x median
            execution_slippage=0.001
        )
    assert "System halted" in str(excinfo.value)
    assert "Bid-ask spread" in str(excinfo.value)

def test_risk_overlay_soft_invariants():
    overlay = RiskOverlay()
    
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 10000.0,
        "avg_cost": 40000.0
    }
    
    orders_sell = [
        ProposedOrder(side="sell", qty=0.1, price=50000.0)
    ]
    overlay.check_invariants(orders_sell, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    
    overlay.check_invariants([], state, btc_price=50000.0, daily_deployed_usdt=0.0)
    
    orders_buy = [
        ProposedOrder(side="buy", qty=0.05, price=50000.0)
    ]
    with pytest.raises(InvariantViolationError) as excinfo:
        overlay.check_invariants(orders_buy, state, btc_price=50000.0, daily_deployed_usdt=0.0)
    assert "INV-2 Violated" in str(excinfo.value)

def test_kill_switch_reserve_floor():
    overlay = RiskOverlay()
    
    with pytest.raises(SystemHaltError) as excinfo:
        overlay.audit_kill_switches(
            drawdown_24h=0.0,
            drawdown_7d=0.0,
            current_reserve_usdt=10000.0,
            total_portfolio_usdt=100000.0,
            api_error_rate_5m=0.0,
            stablecoin_peg_deviations={"USDT": 0.0},
            bid_ask_spread_binance=0.0001,
            median_30d_spread=0.0001,
            execution_slippage=0.0
        )
    assert "Reserve ratio" in str(excinfo.value)

def test_risk_overlay_inv3_limit_order_different_price():
    overlay = RiskOverlay()
    state = {
        "core_btc_qty": 1.0,
        "trading_btc_qty": 0.2,
        "reserve_usdt": 30000.0,
        "avg_cost": 40000.0
    }
    # Current btc_price is 50,000.
    # Limit BUY order is proposed at 48,000 (different from 50,000)
    # The INV-3 check should pass now that it measures conservation of cash flow changes
    orders = [
        ProposedOrder(side="buy", qty=0.05, price=48000.0)
    ]
    overlay.check_invariants(orders, state, btc_price=50000.0, daily_deployed_usdt=0.0)

