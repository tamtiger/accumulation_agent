import numpy as np
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DataGapError(Exception):
    """Raised when there is a missing interval in the market data sequence."""
    pass

class OutlierError(Exception):
    """Raised when incoming market ticks deviate too far from rolling window statistical norms."""
    pass

class MarketTick(BaseModel):
    timestamp: int  # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    liquidations: Optional[float] = None

class DataValidator:
    """
    Validates tick data schemas, checks for timeline gaps, and filters price/volume outliers.
    """
    def __init__(self, expected_interval_sec: int = 60, window_size: int = 100):
        self.expected_interval_sec = expected_interval_sec
        self.window_size = window_size
        self.prices: List[float] = []
        self.volumes: List[float] = []
        self.last_timestamp: Optional[int] = None

    def validate_and_filter(self, tick_data: Dict[str, Any]) -> MarketTick:
        # 1. Schema enforcement
        tick = MarketTick(**tick_data)

        # 2. Gap Detection
        if self.last_timestamp is not None:
            delta_sec = (tick.timestamp - self.last_timestamp) / 1000.0
            if delta_sec > self.expected_interval_sec:
                raise DataGapError(
                    f"Data gap detected: timestamp delta ({delta_sec:.1f}s) > expected interval ({self.expected_interval_sec}s)"
                )
        
        self.last_timestamp = tick.timestamp

        # 3. Store in sliding windows for outlier filtering
        self.prices.append(tick.close)
        self.volumes.append(tick.volume)

        if len(self.prices) > self.window_size:
            self.prices.pop(0)
        if len(self.volumes) > self.window_size:
            self.volumes.pop(0)

        # 4. Outlier Filtering (Rolling z-score on previous 30+ periods)
        # We need a minimum number of elements to calculate meaningful std dev
        if len(self.prices) >= 30:
            # We compute mean/std on all items except the newly appended one
            hist_prices = np.array(self.prices[:-1])
            hist_volumes = np.array(self.volumes[:-1])

            p_mean, p_std = np.mean(hist_prices), np.std(hist_prices)
            v_mean, v_std = np.mean(hist_volumes), np.std(hist_volumes)

            # Price z-score check
            if p_std > 0:
                p_z = abs(tick.close - p_mean) / p_std
                if p_z > 4.5:
                    # Pop the newly added outlier to avoid contaminating future windows
                    self.prices.pop()
                    self.volumes.pop()
                    raise OutlierError(f"Price outlier detected: value={tick.close}, z-score={p_z:.2f} (> 4.5)")

            # Volume z-score check
            if v_std > 0:
                v_z = abs(tick.volume - v_mean) / v_std
                if v_z > 4.5:
                    # Pop the newly added outlier
                    self.prices.pop()
                    self.volumes.pop()
                    raise OutlierError(f"Volume outlier detected: value={tick.volume}, z-score={v_z:.2f} (> 4.5)")

        return tick
