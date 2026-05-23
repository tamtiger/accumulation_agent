import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class RedactorFilter(logging.Filter):
    """
    Filter that redacts passwords, API keys, and sensitive tokens from log messages.
    """
    def __init__(self, name: str = ""):
        super().__init__(name)
        # Regex patterns to find sensitive fields and replace them
        self.patterns = [
            # Postgres connection string password (e.g. postgres://user:pass@host)
            (re.compile(r"(postgresql\+?[a-zA-Z0-9]*://[^:]+:)([^@/]+)(@)"), r"\1REDACTED\3"),
            # Redis URL password (e.g. redis://:pass@host)
            (re.compile(r"(redis://:[^:]+:)([^@/]+)(@)"), r"\1REDACTED\3"),
            # API key parameters: "apiKey": "xyz" or api_key = "xyz"
            (re.compile(r"(?i)(api_?key['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"), r"\1REDACTED\3"),
            # Secret parameters: "secret": "xyz" or secret = "xyz"
            (re.compile(r"(?i)(secret['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"), r"\1REDACTED\3"),
            # Telegram bot tokens (e.g., bot123456:ABC-DEF)
            (re.compile(r"(?i)(bot\d+:)([A-Za-z0-9_-]{35})"), r"\1REDACTED")
        ]

    def redact(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True

class JSONFormatter(logging.Formatter):
    """
    Formats log records as structured JSON.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "agent_name": getattr(record, "agent_name", "system")
        }

        # Inject extra attributes useful for ABAS agents
        tick_id = getattr(record, "tick_id", None)
        action = getattr(record, "action", None)
        state_snapshot = getattr(record, "state_snapshot", None)
        metadata = getattr(record, "metadata", None)

        if tick_id is not None:
            log_data["tick_id"] = tick_id
        if action is not None:
            log_data["action"] = action
        if state_snapshot is not None:
            log_data["state_snapshot"] = state_snapshot
        if metadata is not None:
            log_data["metadata"] = metadata

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logging(level: int = logging.INFO) -> None:
    """
    Sets up the global logging configuration to use the JSON formatter and Redactor filter.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clean existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RedactorFilter())
    root_logger.addHandler(handler)

class AgentLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter that injects agent metadata into log records.
    """
    def log(self, level: int, msg: Any, *args: Any, **kwargs: Any) -> None:
        extra = self.extra.copy() if self.extra else {}
        
        # Allow overriding agent metadata on a per-call basis
        for key in ["tick_id", "action", "state_snapshot", "metadata"]:
            if key in kwargs:
                extra[key] = kwargs.pop(key)
                
        kwargs["extra"] = extra
        super().log(level, msg, *args, **kwargs)

def get_agent_logger(agent_name: str) -> AgentLoggerAdapter:
    """
    Factory function to retrieve a logger adapted for a specific agent.
    """
    logger = logging.getLogger(agent_name)
    return AgentLoggerAdapter(logger, {"agent_name": agent_name})
