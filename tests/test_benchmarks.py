import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.backtest.benchmarks import (
    run_passive_hodl,
    run_weekly_dca,
    run_core_plus_weekly_dca,
    run_fixed_grid_backtest
)

@pytest.fixture
def mock_db_and_orchestrator():
    # Patch all database operations
    with patch("src.backtest.harness.BacktestHarness._reset_database"), \
         patch("src.backtest.harness.BacktestHarness._get_total_realized_pnl", return_value=5000.0), \
         patch("src.inventory.models.InventoryRepository.save_lot"), \
         patch("src.inventory.models.InventoryRepository.update_lot_status"), \
         patch("src.inventory.models.InventoryRepository.save_portfolio_state"), \
         patch("src.inventory.models.InventoryRepository.save_trade_history"), \
         patch("src.inventory.models.InventoryRepository.get_active_lots", return_value=[]), \
         patch("src.execution.orchestrator.ABASOrchestrator.save_raw_ohlcv_to_db"), \
         patch("src.execution.orchestrator.ABASOrchestrator.get_daily_deployed_usdt", return_value=0.0):
        yield

def test_benchmarks_run(mock_db_and_orchestrator):
    """
    Verifies that the HODL, weekly DCA, core + weekly DCA, and fixed grid benchmarks run successfully.
    """
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=168 * 2, freq="h")  # 2 weeks
    prices = 30000.0 + np.cumsum(np.random.normal(5, 50, 168 * 2))
    highs = prices + 10.0
    lows = prices - 10.0
    opens = prices - 5.0
    volumes = np.random.uniform(50, 200, 168 * 2)

    df = pd.DataFrame({
        "time": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes
    })

    # Test HODL
    hodl_val = run_passive_hodl(df, initial_usdt=100000.0, initial_core_btc=0.0)
    assert hodl_val > 0

    # Test Weekly DCA
    dca_val = run_weekly_dca(df, initial_usdt=100000.0, initial_core_btc=0.0)
    assert dca_val > 0

    # Test Core + Weekly DCA
    core_dca_val = run_core_plus_weekly_dca(df, initial_usdt=100000.0, initial_core_btc=0.0)
    assert core_dca_val > 0

    # Test Fixed Grid Backtest
    grid_res = run_fixed_grid_backtest(df, initial_usdt=100000.0, initial_core_btc=0.0)
    assert grid_res["after_tax_total_btc"] > 0
