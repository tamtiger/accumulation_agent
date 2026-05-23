import pytest
from src.portfolio.tracker import PortfolioTracker

def test_portfolio_reconciliation_pass():
    tracker = PortfolioTracker()
    
    # Check within 0.01% limit -> should pass (return True)
    assert tracker.reconcile_balances(
        exchange_usdt=10000.0,
        exchange_btc=0.5,
        db_reserve_usdt=10000.0,
        db_trading_btc=0.5
    ) is True

    # Check exactly at 0.005% discrepancy -> should pass
    assert tracker.reconcile_balances(
        exchange_usdt=10000.5,  # 0.005% difference
        exchange_btc=0.5,
        db_reserve_usdt=10000.0,
        db_trading_btc=0.5
    ) is True

def test_portfolio_reconciliation_fail():
    tracker = PortfolioTracker()
    
    # 0.1% discrepancy in USDT (exceeds 0.01% cap) -> should fail (return False)
    assert tracker.reconcile_balances(
        exchange_usdt=10015.0,  # 0.15% difference
        exchange_btc=0.5,
        db_reserve_usdt=10000.0,
        db_trading_btc=0.5
    ) is False

    # 1.0% discrepancy in BTC -> should fail
    assert tracker.reconcile_balances(
        exchange_usdt=10000.0,
        exchange_btc=0.505,  # 1% difference
        db_reserve_usdt=10000.0,
        db_trading_btc=0.5
    ) is False

def test_exposure_monitoring():
    tracker = PortfolioTracker(hot_exchange_cap=0.25)
    
    # Total portfolio = 50,000 USDT + 0.2 BTC * 50,000 = 60,000 USDT.
    # Hot exchange val = 0.2 * 50,000 = 10,000 (16.6% exposure < 25% cap)
    exposure = tracker.monitor_exposure(
        trading_btc_qty=0.2,
        core_btc_qty=1.0,
        reserve_usdt=50000.0,
        btc_price=50000.0
    )
    assert abs(exposure - 0.09090909) < 1e-5

    # High exposure:
    # Total portfolio = 10,000 USDT + 0.8 BTC * 50,000 = 50,000 USDT.
    # Hot exchange val = 0.8 * 50,000 = 40,000 (80% exposure > 25% cap)
    exposure_high = tracker.monitor_exposure(
        trading_btc_qty=0.8,
        core_btc_qty=0.0,
        reserve_usdt=10000.0,
        btc_price=50000.0
    )
    assert exposure_high == 0.80
