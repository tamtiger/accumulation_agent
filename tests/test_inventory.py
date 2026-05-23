import datetime
from unittest.mock import patch
import pytest
from hypothesis import given, strategies as st
from src.inventory.ledger import FIFOLedger
from src.inventory.models import TradeLot

# Mock repository to prevent DB execution during tests
@pytest.fixture(autouse=True)
def mock_db_repo():
    with patch("src.inventory.models.InventoryRepository.save_lot", return_value=1), \
         patch("src.inventory.models.InventoryRepository.update_lot_status"), \
         patch("src.inventory.models.InventoryRepository.save_trade_history"):
        yield

def test_ledger_buy_sell():
    ledger = FIFOLedger()
    ledger.reserve_usdt = 100000.0
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Buy 1 BTC at 50,000
    ledger.add_buy_lot(1.0, 50000.0, now, "regime_1")
    assert ledger.trading_btc_qty == 1.0
    assert ledger.reserve_usdt == 50000.0
    assert ledger.avg_cost == 50000.0
    
    # Buy 1 BTC at 60,000
    ledger.add_buy_lot(1.0, 60000.0, now, "regime_1")
    assert ledger.trading_btc_qty == 2.0
    assert ledger.reserve_usdt == -10000.0
    assert ledger.avg_cost == 55000.0
    
    # Sell 1.5 BTC at 70,000
    pnl = ledger.consume_sell_lots(1.5, 70000.0, now, "order_1")
    
    # FIFO logic:
    # First lot (1.0 at 50k) fully consumed -> PnL = (70k - 50k) * 1.0 = 20k
    # Second lot (1.0 at 60k) half consumed -> PnL = (70k - 60k) * 0.5 = 5k
    # Total PnL = 25k
    assert pnl == 25000.0
    assert ledger.trading_btc_qty == 0.5
    assert ledger.avg_cost == 60000.0  # remaining 0.5 BTC of the second lot

# Hypothesis property-based test
@given(
    buys=st.lists(
        st.tuples(
            st.floats(min_value=0.01, max_value=10.0),       # qty
            st.floats(min_value=1000.0, max_value=100000.0)  # price
        ),
        min_size=1, max_size=10
    ),
    sell_fraction=st.floats(min_value=0.1, max_value=0.9)
)
def test_hypothesis_fifo_conservation(buys, sell_fraction):
    ledger = FIFOLedger()
    # Provide a huge initial cash buffer to avoid negative reserves issues during test
    ledger.reserve_usdt = 10000000.0
    now = datetime.datetime.now(datetime.timezone.utc)
    
    total_bought_qty = 0.0
    total_spent_usdt = 0.0
    
    # Perform all buys
    for qty, price in buys:
        ledger.add_buy_lot(qty, price, now, "test")
        total_bought_qty += qty
        total_spent_usdt += qty * price

    assert abs(ledger.trading_btc_qty - total_bought_qty) < 1e-7
    
    # Calculate average cost before sell
    expected_avg_cost = total_spent_usdt / total_bought_qty
    assert abs(ledger.avg_cost - expected_avg_cost) < 1e-7
    
    # Sell a fraction of total bought quantity
    sell_qty = total_bought_qty * sell_fraction
    sell_price = 150000.0
    pnl = ledger.consume_sell_lots(sell_qty, sell_price, now, "sell_order")
    
    # Verify conservation: final BTC qty must match original minus sold
    assert abs(ledger.trading_btc_qty - (total_bought_qty - sell_qty)) < 1e-7
    
    # Verify that total assets value is conserved:
    # Portfolio value in USDT = reserve_usdt + trading_btc_qty * sell_price
    # After-sell portfolio value must equal pre-sell value (measured at sell_price) plus realized pnl?
    # No: sell_qty * sell_price is added to reserve, sell_qty of BTC is removed.
    # USDT cash increases by sell_qty * sell_price, which is exactly the amount subtracted from the BTC sleeve.
    # Therefore, the sum (reserve_usdt + trading_btc_qty * sell_price) must be strictly identical before and after.
    # Pre-sell portfolio value = (10000000 - total_spent_usdt) + total_bought_qty * sell_price
    # Post-sell portfolio value = reserve_usdt + trading_btc_qty * sell_price
    pre_sell_val = (10000000.0 - total_spent_usdt) + total_bought_qty * sell_price
    post_sell_val = ledger.reserve_usdt + ledger.trading_btc_qty * sell_price
    assert abs(pre_sell_val - post_sell_val) < 1e-7
