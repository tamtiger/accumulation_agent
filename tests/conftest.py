import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True, scope="session")
def mock_external_services():
    # Mock redis.from_url globally for all tests
    mock_redis = MagicMock()
    
    # Mock psycopg2 connection and pool globally
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    
    with patch("redis.from_url", return_value=mock_redis), \
         patch("psycopg2.pool.SimpleConnectionPool", return_value=mock_pool), \
         patch("psycopg2.connect", return_value=mock_conn):
        yield
