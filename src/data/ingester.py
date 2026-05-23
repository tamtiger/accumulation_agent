import json
import logging
import uuid
from typing import Any, Dict, Optional
import ccxt
import redis
from src.config import settings
from src.data.validators import DataValidator, DataGapError, OutlierError
from src.utils.logging import get_agent_logger

logger = get_agent_logger("data_agent")

class DataIngester:
    """
    Ingests market data from Binance via CCXT, validates it, and publishes it to Redis.
    """
    def __init__(self, symbol: str = "BTC/USDT", interval: str = "1m", redis_client: Optional[redis.Redis] = None):
        self.symbol = symbol
        self.interval = interval
        self.redis_url = settings.redis_url
        self._redis_client = redis_client
        self.validator = DataValidator(expected_interval_sec=self._interval_to_seconds(interval))

        # CCXT Binance initialization
        exchange_kwargs = {
            "enableRateLimit": settings.binance_enable_rate_limit,
        }
        if settings.binance_api_key:
            exchange_kwargs["apiKey"] = settings.binance_api_key
        if settings.binance_secret:
            exchange_kwargs["secret"] = settings.binance_secret

        self.exchange = ccxt.binance(exchange_kwargs)

    @property
    def redis_client(self) -> redis.Redis:
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url)
        return self._redis_client

    def _interval_to_seconds(self, interval: str) -> int:
        unit = interval[-1]
        amount = int(interval[:-1])
        if unit == "m":
            return amount * 60
        elif unit == "h":
            return amount * 3600
        elif unit == "d":
            return amount * 86400
        return 60

    def fetch_latest_tick(self) -> Dict[str, Any]:
        """
        Fetches the latest completed candle and derivative details from Binance.
        """
        # Fetch OHLCV candles (limit=2, since the last one is still building, we fetch the previous completed one)
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.interval, limit=2)
        if not ohlcv or len(ohlcv) < 2:
            raise ValueError("Insufficient OHLCV data returned from exchange.")

        completed_candle = ohlcv[0]  # First one is the last closed candle
        timestamp, open_val, high, low, close, volume = completed_candle

        # Fetch Perp Funding rate
        funding_rate = None
        try:
            # Binance USDT perpetual notation is symbol:USDT (e.g. BTC/USDT:USDT)
            perp_symbol = f"{self.symbol.split('/')[0]}/{self.symbol.split('/')[1]}:{self.symbol.split('/')[1]}"
            funding_info = self.exchange.fetch_funding_rate(perp_symbol)
            funding_rate = funding_info.get("fundingRate")
        except Exception as e:
            logger.warning(f"Failed to fetch perp funding rate: {e}")

        # Fetch Open Interest
        open_interest = None
        try:
            perp_symbol = f"{self.symbol.split('/')[0]}/{self.symbol.split('/')[1]}:{self.symbol.split('/')[1]}"
            oi_info = self.exchange.fetch_open_interest(perp_symbol)
            open_interest = oi_info.get("openInterest")
        except Exception as e:
            logger.warning(f"Failed to fetch open interest: {e}")

        liquidations = 0.0  # CCXT does not standardize liquidations natively; defaulting to 0.0

        return {
            "timestamp": timestamp,
            "open": float(open_val),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": float(volume),
            "funding_rate": float(funding_rate) if funding_rate is not None else None,
            "open_interest": float(open_interest) if open_interest is not None else None,
            "liquidations": float(liquidations)
        }

    def ingest_tick(self) -> Optional[Dict[str, Any]]:
        """
        Fetches, validates, and publishes a new market tick to the Redis Pub/Sub backplane.
        """
        raw_tick = self.fetch_latest_tick()
        try:
            validated_tick = self.validator.validate_and_filter(raw_tick)
            tick_dict = validated_tick.model_dump()

            payload = {
                "message_id": str(uuid.uuid4()),
                "timestamp": validated_tick.timestamp,
                "sender": "data_agent",
                "recipient": "feature_agent",
                "payload": tick_dict
            }
            # Publish to Redis Pub/Sub
            self.redis_client.publish("broadcast:market_data", json.dumps(payload))
            logger.info(
                f"Tick ingested successfully: price={tick_dict['close']}, vol={tick_dict['volume']}",
                action="ingest_tick",
                metadata={"tick": tick_dict}
            )
            return tick_dict

        except DataGapError as e:
            logger.error(f"Data gap event triggered: {e}", action="data_gap_event")
            raise e
        except OutlierError as e:
            logger.warning(f"Tick quarantined as outlier: {e}", action="outlier_quarantine")
            # Do not pass outlier tick to downstream agents
            return None
