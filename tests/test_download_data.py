import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.backtest.download_data import download_historical_data

@patch("src.backtest.download_data.ccxt.binance")
def test_download_historical_data(mock_binance_class, tmp_path):
    # Setup mock exchange
    mock_exchange = MagicMock()
    mock_binance_class.return_value = mock_exchange
    
    # Mock parse8601 and iso8601
    mock_exchange.parse8601.side_effect = lambda x: 1514764800000 if "2018-01-01T00:00:00Z" in x else 1514772000000
    mock_exchange.iso8601.side_effect = lambda x: "2018-01-01T00:00:00Z"
    mock_exchange.rateLimit = 100
    
    # Mock fetch_ohlcv returns 2 hours of data
    mock_exchange.fetch_ohlcv.return_value = [
        [1514764800000, 10000.0, 10100.0, 9900.0, 10050.0, 100.0],
        [1514768400000, 10050.0, 10200.0, 10000.0, 10150.0, 150.0]
    ]
    
    output_file = tmp_path / "test_download.parquet"
    
    download_historical_data(
        symbol="BTC/USDT",
        timeframe="1h",
        start_str="2018-01-01T00:00:00Z",
        end_str="2018-01-01T02:00:00Z",
        output_path=str(output_file)
    )
    
    # Verify file was written
    assert output_file.exists()
    df = pd.read_parquet(output_file)
    assert len(df) == 2
    assert df.iloc[0]["close"] == 10050.0
    assert df.iloc[1]["close"] == 10150.0
