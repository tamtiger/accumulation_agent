import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import settings
from src.utils.db import get_connection, release_connection

logger = logging.getLogger("feature_agent")

class FeatureEngine:
    """
    Computes technical indicators and reference anchors for market ticks.
    Supports both batch DataFrame processing (for backtesting) and single-tick online processing (from database).
    """

    @staticmethod
    def calculate_anchors_and_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized feature calculations on a pandas DataFrame.
        Expected columns: ['time', 'open', 'high', 'low', 'close', 'volume', 'funding_rate', 'open_interest', 'liquidations']
        """
        # Ensure sorted by time
        df = df.sort_values('time').copy()
        if len(df) == 0:
            return df

        # We set a datetime index temporarily for resampling operations
        df_idx = df.set_index(pd.to_datetime(df['time'], utc=True))

        # 1. Daily resampled indicators (EMA200 Macro, 30d high, 30d realized volatility)
        df_daily = df_idx.resample('D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        # Calculate daily anchors
        if len(df_daily) >= 2:
            df_daily['ema200_1d'] = df_daily['close'].ewm(span=200, adjust=False).mean()
            df_daily['ema200_1d_slope'] = df_daily['ema200_1d'].diff()

            # A_range: Rolling 30-day max high
            df_daily['a_range'] = df_daily['high'].rolling(min(30, len(df_daily))).max()

            # Daily realized vol -> 30d annualized
            df_daily['log_returns'] = np.log(df_daily['close'] / df_daily['close'].shift(1))
            daily_vol_window = min(30, len(df_daily) - 1)
            if daily_vol_window > 2:
                df_daily['realized_vol_daily'] = df_daily['log_returns'].rolling(daily_vol_window).std()
                df_daily['sigma_ann'] = df_daily['realized_vol_daily'] * np.sqrt(365)
            else:
                df_daily['sigma_ann'] = 0.40  # Default fallback 40%

            # ATR(14) / price
            high_d = df_daily['high']
            low_d = df_daily['low']
            close_prev_d = df_daily['close'].shift(1)
            tr_d = pd.concat([
                high_d - low_d,
                (high_d - close_prev_d).abs(),
                (low_d - close_prev_d).abs()
            ], axis=1).max(axis=1)
            df_daily['atr14'] = tr_d.rolling(min(14, len(df_daily))).mean()
            df_daily['a_vol'] = df_daily['atr14'] / df_daily['close']
        else:
            # Fallbacks for very small datasets
            df_daily['ema200_1d'] = df_daily['close']
            df_daily['ema200_1d_slope'] = 0.0
            df_daily['a_range'] = df_daily['high']
            df_daily['sigma_ann'] = 0.40
            df_daily['a_vol'] = 0.02  # 2% default ATR

        # 2. 4h resampled indicators (EMA20, EMA50, EMA200)
        df_4h = df_idx.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if len(df_4h) >= 2:
            df_4h['ema20_4h'] = df_4h['close'].ewm(span=20, adjust=False).mean()
            df_4h['ema50_4h'] = df_4h['close'].ewm(span=50, adjust=False).mean()
            df_4h['ema200_4h'] = df_4h['close'].ewm(span=200, adjust=False).mean()

            df_4h['ema20_4h_slope'] = df_4h['ema20_4h'].diff()
            df_4h['ema50_4h_slope'] = df_4h['ema50_4h'].diff()
            df_4h['ema200_4h_slope'] = df_4h['ema200_4h'].diff()

            # RSI(14) on 4h
            delta_4h = df_4h['close'].diff()
            gain = (delta_4h.where(delta_4h > 0, 0)).rolling(min(14, len(df_4h))).mean()
            loss = (-delta_4h.where(delta_4h < 0, 0)).rolling(min(14, len(df_4h))).mean()
            rs = gain / (loss + 1e-9)
            df_4h['rsi14_4h'] = 100 - (100 / (1 + rs))
        else:
            df_4h['ema20_4h'] = df_4h['close']
            df_4h['ema50_4h'] = df_4h['close']
            df_4h['ema200_4h'] = df_4h['close']
            df_4h['ema20_4h_slope'] = 0.0
            df_4h['ema50_4h_slope'] = 0.0
            df_4h['ema200_4h_slope'] = 0.0
            df_4h['rsi14_4h'] = 50.0

        # 3. Map back to original dataframe (reindex / forward fill)
        df['A_trend'] = df_daily['ema200_1d'].reindex(df_idx.index, method='ffill').values
        df['A_range'] = df_daily['a_range'].reindex(df_idx.index, method='ffill').values
        df['sigma_ann'] = df_daily['sigma_ann'].reindex(df_idx.index, method='ffill').values
        df['A_vol'] = df_daily['a_vol'].reindex(df_idx.index, method='ffill').values
        df['A_mean'] = df_4h['ema20_4h'].reindex(df_idx.index, method='ffill').values

        # Slope features mapped back
        df['ema20_4h_slope'] = df_4h['ema20_4h_slope'].reindex(df_idx.index, method='ffill').values
        df['ema50_4h_slope'] = df_4h['ema50_4h_slope'].reindex(df_idx.index, method='ffill').values
        df['ema200_4h_slope'] = df_4h['ema200_4h_slope'].reindex(df_idx.index, method='ffill').values
        df['ema200_1d_slope'] = df_daily['ema200_1d_slope'].reindex(df_idx.index, method='ffill').values
        df['rsi'] = df_4h['rsi14_4h'].reindex(df_idx.index, method='ffill').values

        # 4. Hourly / Tick level features (relative to window size)
        # 30-day window for volume profile z-score (assuming 1h ticks = 30 * 24 = 720 periods)
        rolling_window = min(720, len(df))
        if rolling_window > 2:
            mean_v = df['volume'].rolling(rolling_window).mean()
            std_v = df['volume'].rolling(rolling_window).std()
            df['volume_zscore'] = (df['volume'] - mean_v) / (std_v + 1e-9)

            # deltas over 24h (assuming 1h intervals)
            # If resolution is different, we can shift by hours
            shift_periods = min(24, len(df) - 1)
            df['funding_rate_delta_24h'] = df['funding_rate'].diff(shift_periods) if 'funding_rate' in df.columns else 0.0
            df['open_interest_delta_24h'] = df['open_interest'].diff(shift_periods) if 'open_interest' in df.columns else 0.0
            
            # Liquidation intensity: rolling sum of liquidations
            df['liquidation_intensity'] = df['liquidations'].rolling(shift_periods).sum() if 'liquidations' in df.columns else 0.0
        else:
            df['volume_zscore'] = 0.0
            df['funding_rate_delta_24h'] = 0.0
            df['open_interest_delta_24h'] = 0.0
            df['liquidation_intensity'] = 0.0

        # Replace NaN with 0 or fallback values
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        df.fillna(0.0, inplace=True)

        return df

    def compute_latest_features(self, limit: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Online Mode: Queries TimescaleDB for the latest `limit` ticks, computes
        vectorized features, and returns the feature dictionary of the latest tick.
        """
        conn = None
        try:
            conn = get_connection()
            query = """
                SELECT time, open, high, low, close, volume, funding_rate, open_interest, liquidations
                FROM binance_ohlcv
                ORDER BY time DESC
                LIMIT %s
            """
            df_db = pd.read_sql_query(query, conn, params=(limit,))
            if df_db.empty:
                logger.warning("No historical data found in database to calculate features.")
                return None

            # Reverse to chronological order for calculations
            df_db = df_db.iloc[::-1].reset_index(drop=True)

            # Execute calculations
            df_features = self.calculate_anchors_and_features(df_db)

            # Return the last row (latest tick) as a dict
            latest_tick_features = df_features.iloc[-1].to_dict()
            
            # Convert timestamp to string if needed
            if isinstance(latest_tick_features['time'], pd.Timestamp):
                latest_tick_features['time'] = latest_tick_features['time'].isoformat()

            return latest_tick_features
        except Exception as e:
            logger.error(f"Error computing latest features: {e}")
            return None
        finally:
            if conn:
                release_connection(conn)
