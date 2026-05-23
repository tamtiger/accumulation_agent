import datetime
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from src.backtest.harness import BacktestHarness
from src.risk.overlay import ProposedOrder

@pytest.fixture
def mock_db_and_orchestrator():
    # Patch all database operations
    with patch("src.backtest.harness.BacktestHarness._reset_database"), \
         patch("src.backtest.harness.BacktestHarness._get_total_realized_pnl", return_value=12000.0), \
         patch("src.inventory.models.InventoryRepository.save_lot"), \
         patch("src.inventory.models.InventoryRepository.update_lot_status"), \
         patch("src.inventory.models.InventoryRepository.save_portfolio_state"), \
         patch("src.inventory.models.InventoryRepository.save_trade_history"), \
         patch("src.inventory.models.InventoryRepository.get_active_lots", return_value=[]), \
         patch("src.execution.orchestrator.ABASOrchestrator.save_raw_ohlcv_to_db"), \
         patch("src.execution.orchestrator.ABASOrchestrator.get_daily_deployed_usdt", return_value=0.0):
        yield

def test_backtest_harness_run(mock_db_and_orchestrator):
    # Setup mock data (50 hours)
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=100, freq="h")
    prices = 30000.0 + np.cumsum(np.random.normal(5, 50, 100))
    highs = prices + 10.0
    lows = prices - 10.0
    opens = prices - 5.0
    volumes = np.random.uniform(50, 200, 100)

    df = pd.DataFrame({
        "time": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes
    })

    # Instantiate harness
    harness = BacktestHarness(
        initial_usdt=100000.0,
        initial_core_btc=0.5,
        tax_rate=0.20
    )

    # Mock the feature engine to return predefined features matching the latest price
    # so we don't have to populate a real SQL db in the mock test
    def mock_compute_latest_features(limit=500):
        current_close = harness.orchestrator.exchange.orders.values()
        # just return standard mock features
        return {
            "close": df.iloc[-1]["close"],
            "A_trend": 30000.0,
            "A_range": 32000.0,
            "A_mean": 30500.0,
            "sigma_ann": 0.40
        }
    
    harness.orchestrator.features_engine.compute_latest_features = mock_compute_latest_features

    # Run backtest
    results = harness.run(df)

    # Assert outputs
    assert results["initial_portfolio_usdt"] == 100000.0 + 0.5 * df.iloc[0]["close"]
    assert results["hodl_benchmark_btc"] > 0
    assert results["pre_tax_total_btc"] > 0
    assert results["after_tax_total_btc"] > 0
    assert results["tax_liability_usdt"] == 12000.0 * 0.20
    assert "pre_tax_outperformance_btc" in results
    assert "after_tax_outperformance_btc" in results
