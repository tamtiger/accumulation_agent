import os
import shutil
from unittest.mock import MagicMock
from src.portfolio.reconcile_audit import LedgerAuditor

def test_ledger_auditor_pass(monkeypatch):
    # Setup mock exchange
    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {
        "free": {"USDT": 10000.0, "BTC": 0.5}
    }
    
    # Mock Telegram Notifier
    mock_notifier = MagicMock()
    
    auditor = LedgerAuditor(mock_exchange, mock_notifier)
    
    # Mock ledger DB returns matching state
    mock_state = {
        "reserve_usdt": 10000.0,
        "trading_btc_qty": 0.5
    }
    auditor.ledger.get_state_snapshot = MagicMock(return_value=mock_state)
    auditor.ledger.load_from_db = MagicMock()
    
    # Run audit
    report = auditor.run_daily_audit()
    
    assert report["audit_passed"] is True
    assert report["discrepancies"]["USDT_pct"] == 0.0
    assert report["discrepancies"]["BTC_pct"] == 0.0
    assert not mock_notifier.send_alert.called
    
    # Verify report is written
    filename = f"data/audits/audit_{report['timestamp'][:10].replace('-', '')}.json"
    assert os.path.exists(filename)
    
    # Clean up audits folder after test
    if os.path.exists("data/audits"):
        shutil.rmtree("data/audits")

def test_ledger_auditor_fail():
    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {
        "free": {"USDT": 10000.0, "BTC": 0.5}
    }
    
    mock_notifier = MagicMock()
    auditor = LedgerAuditor(mock_exchange, mock_notifier)
    
    # Mock mismatching state
    mock_state = {
        "reserve_usdt": 9000.0, # 10% discrepancy
        "trading_btc_qty": 0.5
    }
    auditor.ledger.get_state_snapshot = MagicMock(return_value=mock_state)
    auditor.ledger.load_from_db = MagicMock()
    
    report = auditor.run_daily_audit()
    
    assert report["audit_passed"] is False
    assert report["discrepancies"]["USDT_pct"] > 0.0
    assert mock_notifier.send_alert.called
    
    # Clean up audits folder
    if os.path.exists("data/audits"):
        shutil.rmtree("data/audits")
