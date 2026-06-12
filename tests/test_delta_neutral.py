import pytest
import os
from unittest.mock import patch, MagicMock
from src.execution.orchestrator import ABASOrchestrator
from src.execution.delta_neutral import DeltaNeutralManager
from src.config import settings

@pytest.fixture
def mock_db_ops():
    # Patch database persistence to prevent live database requirements
    with patch("src.inventory.models.InventoryRepository.save_lot"), \
         patch("src.inventory.models.InventoryRepository.update_lot_status"), \
         patch("src.inventory.models.InventoryRepository.save_portfolio_state") as mock_save_state, \
         patch("src.inventory.models.InventoryRepository.save_trade_history"), \
         patch("src.inventory.models.InventoryRepository.get_active_lots", return_value=[]), \
         patch("src.execution.orchestrator.ABASOrchestrator.save_raw_ohlcv_to_db"), \
         patch("src.execution.orchestrator.ABASOrchestrator.get_daily_deployed_usdt", return_value=0.0):
        yield mock_save_state

def test_delta_neutral_engine():
    # Test DeltaNeutralManager execute_tick logic in isolation
    mock_exchange = MagicMock()
    manager = DeltaNeutralManager(mock_exchange)
    
    # Ensure ledger is clean
    if os.path.exists(manager.ledger_file):
        os.remove(manager.ledger_file)
    manager.spot_qty = 0.0
    manager.perp_qty = 0.0
    manager.is_active = False
    
    # 1. Normal funding (0.01% per 8h): Should not activate
    orders = manager.execute_tick(
        spot_price=50000.0,
        perp_price=50000.0,
        funding_rate=0.0001,
        total_portfolio_val_usdt=100000.0
    )
    assert len(orders) == 0
    assert not manager.is_active

    # 2. High funding (0.06% per 8h): Should open spot-long & perp-short
    orders = manager.execute_tick(
        spot_price=50000.0,
        perp_price=50050.0,
        funding_rate=0.0006,
        total_portfolio_val_usdt=100000.0
    )
    assert len(orders) == 2
    assert manager.is_active
    assert manager.spot_qty > 0.0
    assert manager.perp_qty > 0.0
    
    # 3. Accumulate funding on active sleeve
    old_accumulated = manager.accumulated_funding_usdt
    manager.execute_tick(
        spot_price=50000.0,
        perp_price=50050.0,
        funding_rate=0.0006,
        total_portfolio_val_usdt=100000.0
    )
    assert manager.accumulated_funding_usdt > old_accumulated

    # 4. Risk check: Basis divergence (perp price drops significantly below spot)
    # perp = 48000, spot = 50000 -> spread = (48k - 50k)/50k = -4% (< -2%)
    assert manager.check_risk(spot_price=50000.0, perp_price=48000.0) is True

    # 5. Risk check: Liquidation proximity
    # entry_price = 50000. Liquidation at ~60000 (5x leverage). perp_price = 58000.
    # distance = (60k - 58k)/58k = 3.4% (< 5%)
    assert manager.check_risk(spot_price=50000.0, perp_price=58000.0) is True

    # 6. Low funding drops below threshold: Should close
    orders = manager.execute_tick(
        spot_price=50000.0,
        perp_price=50000.0,
        funding_rate=0.00005,
        total_portfolio_val_usdt=100000.0
    )
    assert len(orders) == 2
    assert not manager.is_active
    assert manager.spot_qty == 0.0

    # Cleanup
    if os.path.exists(manager.ledger_file):
        os.remove(manager.ledger_file)


def test_orchestrator_delta_neutral_integration(mock_db_ops):
    # Initialize orchestrator in mock mode with delta-neutral enabled
    settings.delta_neutral_enabled = True
    orchestrator = ABASOrchestrator(use_mock=True)
    
    # Clean up ledger file
    if os.path.exists(orchestrator.delta_neutral_manager.ledger_file):
        os.remove(orchestrator.delta_neutral_manager.ledger_file)
    orchestrator.delta_neutral_manager.spot_qty = 0.0
    orchestrator.delta_neutral_manager.perp_qty = 0.0
    orchestrator.delta_neutral_manager.is_active = False

    # Mock features to trigger high funding
    tick = {
        "timestamp": 1609459200000,
        "open": 50000.0, "high": 50500.0, "low": 49800.0, "close": 50000.0, "volume": 150.0,
        "funding_rate": 0.0006, "open_interest": 50000.0, "liquidations": 0.0
    }
    orchestrator.ingester.fetch_latest_tick = MagicMock(return_value=tick)
    
    features = {
        "close": 50000.0,
        "A_trend": 50000.0,
        "A_range": 50000.0,
        "A_mean": 50000.0,
        "sigma_ann": 0.35,
        "A_local_low_48h": 49800.0,
        "funding_rate": 0.0006
    }
    orchestrator.features_engine.compute_latest_features = MagicMock(return_value=features)

    # Disable core grid sleeve orders for isolation testing (by locking grid sizing to 0)
    orchestrator.grid_engine.calculate_buy_size = MagicMock(return_value=0.0)
    orchestrator.grid_engine.calculate_sell_size = MagicMock(return_value=0.0)

    # Run tick
    orchestrator.run_tick()

    # Verify that delta-neutral manager became active
    assert orchestrator.delta_neutral_manager.is_active is True
    dn_spot_qty = orchestrator.delta_neutral_manager.spot_qty
    assert dn_spot_qty > 0.0

    # Ensure isolation: the delta-neutral spot BTC should not be tracked as grid's trading BTC
    assert orchestrator.ledger.trading_btc_qty == 0.5  # Initial mock amount should remain unchanged for grid

    # Verify that exchange holds both mock spot BTC and isolated perp position
    bal = orchestrator.exchange.fetch_balance()
    assert bal["free"]["BTC"] == 0.5 + dn_spot_qty
    assert orchestrator.exchange.perp_position_qty == dn_spot_qty

    # Cleanup
    if os.path.exists(orchestrator.delta_neutral_manager.ledger_file):
        os.remove(orchestrator.delta_neutral_manager.ledger_file)
    settings.delta_neutral_enabled = False
