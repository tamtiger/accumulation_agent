import pytest
from unittest.mock import MagicMock
from src.execution.live_ws import BinanceWSClient
from src.execution.paper import BinancePaper, SecurityError

def test_binance_ws_client():
    client = BinanceWSClient(symbol="BTCUSDT")
    assert client.symbol == "btcusdt"
    
    # Test message handling for depth update
    msg = {
        "bids": [["30000.0", "1.5"]],
        "asks": [["30100.0", "2.0"]]
    }
    client._handle_message(msg)
    assert client.bid_price == 30000.0
    assert client.ask_price == 30100.0
    assert client.get_mid_price() == 30050.0

def test_binance_paper_execution():
    mock_ccxt = MagicMock()
    mock_ccxt.apiKey = None
    mock_ccxt.fetch_balance.return_value = {
        "free": {"USDT": 10000.0, "BTC": 0.1}
    }
    
    ws_client = BinanceWSClient()
    ws_client.bid_price = 30000.0
    ws_client.ask_price = 30100.0
    
    paper = BinancePaper(mock_ccxt, ws_client)
    paper.initialize_balances()
    
    assert paper.paper_reserve_usdt == 10000.0
    assert paper.paper_trading_btc == 0.1
    
    # Simulating a Buy Order
    order = paper.create_order(
        symbol="BTC/USDT",
        type_val="limit",
        side="buy",
        amount=0.05,
        price=30100.0
    )
    
    # Executed price is ask (30100.0)
    assert order["side"] == "buy"
    assert order["amount"] == 0.05
    assert order["average"] == 30100.0
    
    # New balance check
    # Cost = 0.05 * 30100 = 1505.0. Maker fee = 0.02% (0.301 USDT)
    # Total USDT cost = 1505.301
    assert pytest.approx(paper.paper_reserve_usdt, abs=0.01) == 10000.0 - 1505.301
    assert pytest.approx(paper.paper_trading_btc, abs=0.001) == 0.15

def test_paper_security_audit():
    mock_ccxt = MagicMock()
    # Mock withdrawal enabled -> should raise SecurityError
    mock_ccxt.privateGetAccountAPIKeyPermissions.return_value = {"withdraw": True}
    mock_ccxt.apiKey = "some-key"
    
    ws_client = BinanceWSClient()
    paper = BinancePaper(mock_ccxt, ws_client)
    
    with pytest.raises(SecurityError):
        paper.audit_api_permissions()
