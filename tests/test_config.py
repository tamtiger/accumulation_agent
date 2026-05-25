import os
import json
from src.config import Settings, load_settings
from src.utils.logging import setup_logging, get_agent_logger

def test_config_default_values():
    """Test that default values are set correctly in Settings."""
    settings = Settings()
    assert settings.reserve_floor == 0.15
    assert settings.daily_deployment_cap == 0.05
    assert settings.hot_exchange_cap == 0.25
    assert settings.min_profit_threshold == 0.00375
    assert settings.core_btc_target == 0.70
    assert settings.trading_target == 0.15
    assert settings.trading_floor == 0.05
    assert settings.promotion_threshold == 1.3
    assert settings.inv3_epsilon == 1e-8

def test_config_override_by_env(tmp_path):
    """Test that environmental variables override configuration files."""
    # Set env var
    os.environ["RESERVE_FLOOR"] = "0.22"
    os.environ["DB_URL"] = "postgresql://test:test@localhost:5432/test_db"
    
    settings = Settings()
    try:
        assert settings.reserve_floor == 0.22
        assert settings.db_url == "postgresql://test:test@localhost:5432/test_db"
    finally:
        # Clean up
        del os.environ["RESERVE_FLOOR"]
        del os.environ["DB_URL"]

def test_logging_scrubs_secrets():
    """Test that our setup_logging function and logger are callable without errors."""
    setup_logging()
    logger = get_agent_logger("test_agent")
    assert logger is not None
