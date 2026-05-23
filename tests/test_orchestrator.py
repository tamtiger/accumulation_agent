import pytest
import datetime
from unittest.mock import patch, MagicMock
from src.execution.orchestrator import ABASOrchestrator
from src.risk.overlay import InvariantViolationError

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

def test_orchestrator_tick_cycle(mock_db_ops):
    mock_save_state = mock_db_ops
    
    # Initialize orchestrator in mock mode
    orchestrator = ABASOrchestrator(use_mock=True)
    orchestrator.risk_overlay.hot_exchange_cap = 0.50
    
    # Mock data ingester latest tick return
    tick = {
        "timestamp": 1609459200000,
        "open": 30000.0, "high": 30500.0, "low": 29800.0, "close": 30100.0, "volume": 150.0,
        "funding_rate": 0.0001, "open_interest": 50000.0, "liquidations": 0.0
    }
    orchestrator.ingester.fetch_latest_tick = MagicMock(return_value=tick)
    
    # Mock feature calculations
    features = {
        "close": 30100.0,
        "A_trend": 30000.0,
        "A_range": 32000.0,  # drawdown = (32k - 30.1k)/32k = 5.9% -> triggers 5% deployment
        "A_mean": 30100.0,
        "sigma_ann": 0.35  # spacing = 1.5%
    }
    orchestrator.features_engine.compute_latest_features = MagicMock(return_value=features)
    
    # Pre-balance state: USDT = 50,000, BTC = 0.5
    # Total portfolio val = 50,000 + 0.5 * 30,100 = 65,050
    # Reserve floor = 15% of 65,050 = 9,757.5
    # 5.9% drawdown -> deploy 5% of remaining reserve (5% of 50,000 = 2,500 USDT)
    # 2,500 USDT < 65,050 * 5% daily deployment cap (3,252.5) -> passes cap
    
    # Run tick
    orchestrator.run_tick()
    
    # Verify that save_portfolio_state was called
    assert mock_save_state.called
    
    # Verify that order was executed and mock balance adjusted:
    # Pre-USDT: 50,000. BUY cost: 2,500 + maker fee (0.02% of 2,500 = 0.5) -> next USDT should be ~47,499.5
    # Pre-BTC: 0.5. BUY size: 2,500 / 30,100 = 0.083056 -> next BTC should be ~0.583056
    # Let's verify that exchange balance was updated:
    bal = orchestrator.exchange.fetch_balance()
    assert bal["free"]["BTC"] > 0.5
    assert bal["free"]["USDT"] < 50000.0
