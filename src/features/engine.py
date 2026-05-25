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

        # Calculate rolling low over 48h (12 periods of 4h)
        if len(df_4h) >= 12:
            df_4h['rolling_low_48h'] = df_4h['low'].rolling(12).min()
        else:
            df_4h['rolling_low_48h'] = df_4h['low'].min()

        # 3. Map back to original dataframe (reindex / forward fill)
        df['A_trend'] = df_daily['ema200_1d'].reindex(df_idx.index, method='ffill').values
        df['A_range'] = df_daily['a_range'].reindex(df_idx.index, method='ffill').values
        df['sigma_ann'] = df_daily['sigma_ann'].reindex(df_idx.index, method='ffill').values
        df['A_vol'] = df_daily['a_vol'].reindex(df_idx.index, method='ffill').values
        df['A_mean'] = df_4h['ema20_4h'].reindex(df_idx.index, method='ffill').values
        df['A_local_low_48h'] = df_4h['rolling_low_48h'].reindex(df_idx.index, method='ffill').values

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

    def compute_latest_features(self, limit: int = 1440) -> Optional[Dict[str, Any]]:
        """
        Online Mode: Queries TimescaleDB for resampled daily and 4-hour candles
        plus recent 1-minute ticks to calculate correct indicators for the latest tick.
        """
        conn = None
        try:
            conn = get_connection()
            
            # 1. Fetch daily resampled candles (up to 250 days for daily EMA200)
            daily_query = """
                SELECT date_trunc('day', time) AS time,
                       (array_agg(open ORDER BY time ASC))[1] as open,
                       max(high) as high,
                       min(low) as low,
                       (array_agg(close ORDER BY time DESC))[1] as close,
                       sum(volume) as volume
                FROM binance_ohlcv
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT 250
            """
            df_daily = pd.read_sql_query(daily_query, conn)
            
            # 2. Fetch 4h resampled candles (up to 200 periods for 4h EMA200)
            four_hour_query = """
                SELECT to_timestamp(floor(extract(epoch from time) / 14400) * 14400) AS time,
                       (array_agg(open ORDER BY time ASC))[1] as open,
                       max(high) as high,
                       min(low) as low,
                       (array_agg(close ORDER BY time DESC))[1] as close,
                       sum(volume) as volume
                FROM binance_ohlcv
                GROUP BY 1
                ORDER BY 1 ASC
                LIMIT 200
            """
            df_4h = pd.read_sql_query(four_hour_query, conn)
            
            # 3. Fetch latest 1m ticks (up to 1440 for 24h indicators)
            m1_query = """
                SELECT time, open, high, low, close, volume, funding_rate, open_interest, liquidations
                FROM binance_ohlcv
                ORDER BY time DESC
                LIMIT %s
            """
            df_1m = pd.read_sql_query(m1_query, conn, params=(limit,))
            if df_1m.empty:
                logger.warning("No historical 1m data found in database to calculate features.")
                return None
                
            # Reverse 1m to chronological order
            df_1m = df_1m.iloc[::-1].reset_index(drop=True)
            
            # Calculate daily indicators
            if len(df_daily) >= 2:
                df_daily['ema200_1d'] = df_daily['close'].ewm(span=200, adjust=False).mean()
                df_daily['ema200_1d_slope'] = df_daily['ema200_1d'].diff()
                df_daily['a_range'] = df_daily['high'].rolling(min(30, len(df_daily))).max()
                
                df_daily['log_returns'] = np.log(df_daily['close'] / df_daily['close'].shift(1))
                daily_vol_window = min(30, len(df_daily) - 1)
                if daily_vol_window > 2:
                    df_daily['realized_vol_daily'] = df_daily['log_returns'].rolling(daily_vol_window).std()
                    df_daily['sigma_ann'] = df_daily['realized_vol_daily'] * np.sqrt(365)
                else:
                    df_daily['sigma_ann'] = 0.40
                
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
                df_daily['ema200_1d'] = df_daily['close'] if not df_daily.empty else pd.Series([df_1m['close'].iloc[-1]])
                df_daily['ema200_1d_slope'] = 0.0
                df_daily['a_range'] = df_daily['high'] if not df_daily.empty else pd.Series([df_1m['high'].iloc[-1]])
                df_daily['sigma_ann'] = 0.40
                df_daily['a_vol'] = 0.02

            # Calculate 4h indicators
            if len(df_4h) >= 2:
                df_4h['ema20_4h'] = df_4h['close'].ewm(span=20, adjust=False).mean()
                df_4h['ema50_4h'] = df_4h['close'].ewm(span=50, adjust=False).mean()
                df_4h['ema200_4h'] = df_4h['close'].ewm(span=200, adjust=False).mean()
                
                df_4h['ema20_4h_slope'] = df_4h['ema20_4h'].diff()
                df_4h['ema50_4h_slope'] = df_4h['ema50_4h'].diff()
                df_4h['ema200_4h_slope'] = df_4h['ema200_4h'].diff()
                
                delta_4h = df_4h['close'].diff()
                gain = (delta_4h.where(delta_4h > 0, 0)).rolling(min(14, len(df_4h))).mean()
                loss = (-delta_4h.where(delta_4h < 0, 0)).rolling(min(14, len(df_4h))).mean()
                rs = gain / (loss + 1e-9)
                df_4h['rsi14_4h'] = 100 - (100 / (1 + rs))
            else:
                df_4h['ema20_4h'] = df_4h['close'] if not df_4h.empty else pd.Series([df_1m['close'].iloc[-1]])
                df_4h['ema50_4h'] = df_4h['close'] if not df_4h.empty else pd.Series([df_1m['close'].iloc[-1]])
                df_4h['ema200_4h'] = df_4h['close'] if not df_4h.empty else pd.Series([df_1m['close'].iloc[-1]])
                df_4h['ema20_4h_slope'] = 0.0
                df_4h['ema50_4h_slope'] = 0.0
                df_4h['ema200_4h_slope'] = 0.0
                df_4h['rsi14_4h'] = 50.0

            # Calculate rolling low over 48h (12 periods of 4h)
            if len(df_4h) >= 12:
                df_4h['rolling_low_48h'] = df_4h['low'].rolling(12).min()
            else:
                df_4h['rolling_low_48h'] = df_4h['low'].min() if not df_4h.empty else pd.Series([df_1m['low'].iloc[-1]])

            # Calculate 1m rolling indicators
            rolling_window = min(limit, len(df_1m))
            if rolling_window > 2:
                mean_v = df_1m['volume'].rolling(rolling_window).mean()
                std_v = df_1m['volume'].rolling(rolling_window).std()
                df_1m['volume_zscore'] = (df_1m['volume'] - mean_v) / (std_v + 1e-9)
                
                shift_periods = min(rolling_window - 1, 1440)  # Up to 24h
                df_1m['funding_rate_delta_24h'] = df_1m['funding_rate'].diff(shift_periods) if 'funding_rate' in df_1m.columns else 0.0
                df_1m['open_interest_delta_24h'] = df_1m['open_interest'].diff(shift_periods) if 'open_interest' in df_1m.columns else 0.0
                df_1m['liquidation_intensity'] = df_1m['liquidations'].rolling(shift_periods).sum() if 'liquidations' in df_1m.columns else 0.0
            else:
                df_1m['volume_zscore'] = 0.0
                df_1m['funding_rate_delta_24h'] = 0.0
                df_1m['open_interest_delta_24h'] = 0.0
                df_1m['liquidation_intensity'] = 0.0

            # Merge everything into the latest 1m tick dict
            latest_tick_features = df_1m.iloc[-1].to_dict()
            latest_daily = df_daily.iloc[-1] if not df_daily.empty else {}
            latest_4h = df_4h.iloc[-1] if not df_4h.empty else {}
            
            latest_tick_features["A_trend"] = latest_daily.get("ema200_1d", latest_tick_features["close"])
            latest_tick_features["A_range"] = latest_daily.get("a_range", latest_tick_features["high"])
            latest_tick_features["sigma_ann"] = latest_daily.get("sigma_ann", 0.40)
            latest_tick_features["A_vol"] = latest_daily.get("a_vol", 0.02)
            latest_tick_features["A_mean"] = latest_4h.get("ema20_4h", latest_tick_features["close"])
            latest_tick_features["A_local_low_48h"] = latest_4h.get("rolling_low_48h", latest_tick_features["low"])
            
            latest_tick_features["ema20_4h_slope"] = latest_4h.get("ema20_4h_slope", 0.0)
            latest_tick_features["ema50_4h_slope"] = latest_4h.get("ema50_4h_slope", 0.0)
            latest_tick_features["ema200_4h_slope"] = latest_4h.get("ema200_4h_slope", 0.0)
            latest_tick_features["ema200_1d_slope"] = latest_daily.get("ema200_1d_slope", 0.0)
            latest_tick_features["rsi"] = latest_4h.get("rsi14_4h", 50.0)

            # Replace NaNs with defaults
            for k, v in latest_tick_features.items():
                if pd.isna(v):
                    latest_tick_features[k] = 0.0

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
