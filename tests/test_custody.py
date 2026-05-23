import datetime
import pytest
from unittest.mock import patch, MagicMock
from src.custody.sweeper import CustodySweeper

@pytest.fixture
def mock_db():
    with patch("src.custody.sweeper.get_connection") as mock_conn, \
         patch("src.custody.sweeper.release_connection"):
        # Create mock connection, cursor
        conn_instance = MagicMock()
        cursor_instance = MagicMock()
        mock_conn.return_value = conn_instance
        conn_instance.cursor.return_value.__enter__.return_value = cursor_instance
        yield cursor_instance

def test_sweeper_no_data(mock_db):
    mock_db.fetchall.return_value = []
    sweeper = CustodySweeper(trading_target=0.15, promotion_threshold_multiplier=1.3)
    assert sweeper.check_promotion_trigger() is None

def test_sweeper_insufficient_time_span(mock_db):
    # Only 3 days of records
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_db.fetchall.return_value = [
        (now - datetime.timedelta(days=3), 0.5, 0.5),
        (now, 0.5, 0.5)
    ]
    sweeper = CustodySweeper(trading_target=0.15, promotion_threshold_multiplier=1.3)
    assert sweeper.check_promotion_trigger() is None

def test_sweeper_interrupted_breach(mock_db):
    # Spans 7 days, but on day 4 trading_btc drops below threshold
    now = datetime.datetime.now(datetime.timezone.utc)
    
    records = []
    # Target = 15%, Threshold = 1.3x target = 19.5%
    # If total = 1.0 BTC: threshold qty = 0.195 BTC
    for i in range(8):
        t = now - datetime.timedelta(days=7 - i)
        # Day 4 (i = 4) has trading_btc = 0.15 (below 0.195)
        trading_qty = 0.15 if i == 4 else 0.30
        records.append((t, trading_qty, 0.70))
        
    mock_db.fetchall.return_value = records
    
    sweeper = CustodySweeper(trading_target=0.15, promotion_threshold_multiplier=1.3)
    assert sweeper.check_promotion_trigger() is None

def test_sweeper_successful_trigger(mock_db):
    # Spans 7 days, all records exceed 0.195 BTC (total = 1.0 BTC, trading = 0.30 BTC)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    records = []
    for i in range(8):
        t = now - datetime.timedelta(days=7 - i)
        records.append((t, 0.30, 0.70))
        
    mock_db.fetchall.return_value = records
    
    sweeper = CustodySweeper(trading_target=0.15, promotion_threshold_multiplier=1.3)
    excess = sweeper.check_promotion_trigger()
    
    # Expected excess = trading_qty - total * target = 0.30 - 1.0 * 0.15 = 0.15 BTC
    assert excess is not None
    assert abs(excess - 0.15) < 1e-7
