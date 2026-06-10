import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.backtest.run_simulations import run_abas_backtest

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

def test_backtest_determinism(mock_db_and_orchestrator):
    """
    Asserts that running the identical backtest twice yields identical results.
    """
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

    # Run first time
    res1 = run_abas_backtest(df, initial_usdt=100000.0, initial_core_btc=0.0, tax_rate=0.20)

    # Run second time
    res2 = run_abas_backtest(df, initial_usdt=100000.0, initial_core_btc=0.0, tax_rate=0.20)

    # Assert matching results
    assert res1["pre_tax_total_btc"] == res2["pre_tax_total_btc"]
    assert res1["after_tax_total_btc"] == res2["after_tax_total_btc"]
    assert res1["tax_liability_usdt"] == res2["tax_liability_usdt"]
    assert res1["total_realized_pnl_usdt"] == res2["total_realized_pnl_usdt"]
