import pytest
from src.data.validators import DataValidator, DataGapError, OutlierError

def test_data_validator_schema():
    validator = DataValidator()
    # Test valid input
    tick_data = {
        "timestamp": 1609459200000,
        "open": 29000.0,
        "high": 29200.0,
        "low": 28800.0,
        "close": 29100.0,
        "volume": 120.5,
        "funding_rate": 0.0001,
        "open_interest": 15000.0,
        "liquidations": 0.0
    }
    tick = validator.validate_and_filter(tick_data)
    assert tick.close == 29100.0
    assert tick.volume == 120.5
    assert tick.funding_rate == 0.0001

def test_data_validator_gap():
    # Expected interval 60s
    validator = DataValidator(expected_interval_sec=60)
    
    # First tick
    validator.validate_and_filter({
        "timestamp": 1609459200000,  # 00:00:00
        "open": 29000.0, "high": 29000.0, "low": 29000.0, "close": 29000.0, "volume": 10.0
    })

    # Second tick within 60s (fine)
    validator.validate_and_filter({
        "timestamp": 1609459260000,  # 00:01:00
        "open": 29000.0, "high": 29000.0, "low": 29000.0, "close": 29000.0, "volume": 10.0
    })

    # Third tick 61s after (gap error)
    with pytest.raises(DataGapError):
        validator.validate_and_filter({
            "timestamp": 1609459321000,  # 00:02:01 (61 seconds delta)
            "open": 29000.0, "high": 29000.0, "low": 29000.0, "close": 29000.0, "volume": 10.0
        })

def test_data_validator_outliers():
    validator = DataValidator(window_size=35)
    
    # Feed 30 identical ticks
    for i in range(30):
        validator.validate_and_filter({
            "timestamp": 1609459200000 + (i * 60000),
            "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 10.0
        })
        
    # The 31st tick has close 200.0 (variance is 0 so standard z-score check won't raise unless std > 0,
    # but let's test a spike after some small noise to make std > 0)
    
    validator_noise = DataValidator(window_size=35)
    # Feed noise prices: 99, 100, 101, etc.
    import random
    random.seed(42)
    for i in range(31):
        price = 100.0 + random.uniform(-1.0, 1.0)
        volume = 10.0 + random.uniform(-0.5, 0.5)
        validator_noise.validate_and_filter({
            "timestamp": 1609459200000 + (i * 60000),
            "open": price, "high": price, "low": price, "close": price, "volume": volume
        })
        
    # Now feed a massive outlier price of 500 (standard deviation is around 0.5-0.6, so z-score will be way above 4.5)
    with pytest.raises(OutlierError):
        validator_noise.validate_and_filter({
            "timestamp": 1609459200000 + (31 * 60000),
            "open": 500.0, "high": 500.0, "low": 500.0, "close": 500.0, "volume": 10.0
        })
