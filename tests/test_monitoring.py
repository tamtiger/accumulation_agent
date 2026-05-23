import pytest
from unittest.mock import patch, MagicMock
from src.monitoring.exporter import TelegramNotifier

def test_telegram_notifier_no_env():
    # If token or chat_id is empty, it should output a warning log and return False
    with patch("src.monitoring.exporter.settings.telegram_bot_token", ""), \
         patch("src.monitoring.exporter.settings.telegram_chat_id", ""):
        notifier = TelegramNotifier()
        assert notifier.send_alert("Test message warning fallback") is False

def test_telegram_notifier_success():
    # If credentials exist, it should hit urlopen
    with patch("src.monitoring.exporter.settings.telegram_bot_token", "12345:bottoken"), \
         patch("src.monitoring.exporter.settings.telegram_chat_id", "9876543"):
        notifier = TelegramNotifier()
        
        # Mock urllib.request.urlopen response
        mock_res = MagicMock()
        mock_res.__enter__.return_value.read.return_value = b'{"ok": true}'
        
        with patch("urllib.request.urlopen", return_value=mock_res) as mock_urlopen:
            assert notifier.send_alert("Test status alert message") is True
            assert mock_urlopen.called
