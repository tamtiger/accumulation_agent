import os
import time
import pandas as pd
import numpy as np
import ccxt
from pathlib import Path
from src.data.validators import DataValidator, DataGapError, OutlierError

def download_historical_data(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    start_str: str = "2018-01-01T00:00:00Z",
    end_str: str = "2024-12-31T23:59:59Z",
    output_path: str = "data/btc_1h_binance.parquet"
):
    """
    Downloads historical OHLCV data from Binance, validates it, and caches to Parquet.
    """
    print(f"Initializing download for {symbol} {timeframe} from {start_str} to {end_str}...")
    
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    since = exchange.parse8601(start_str)
    end_ts = exchange.parse8601(end_str)
    
    all_ohlcv = []
    current_since = since
    
    # 1000 candles per fetch limit for Binance
    limit = 1000
    
    while current_since < end_ts:
        try:
            print(f"Fetching candles since {exchange.iso8601(current_since)}...")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)
            if not ohlcv:
                break
                
            all_ohlcv.extend(ohlcv)
            
            # Update since to the timestamp of the last candle + 1 timeframe duration
            last_candle_ts = ohlcv[-1][0]
            current_since = last_candle_ts + 3600000  # 1 hour in ms
            
            # Avoid hitting rate limits
            time.sleep(exchange.rateLimit / 1000.0)
            
            if len(ohlcv) < limit:
                # Reached end of available data
                break
        except Exception as e:
            print(f"Error fetching data: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            
    if not all_ohlcv:
        print("No data retrieved.")
        return
        
    df = pd.DataFrame(all_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    # Convert timestamp to datetime string matching backtest expectations
    df['time'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Drop duplicates if any
    df = df.drop_duplicates(subset=['time']).sort_values('time').reset_index(drop=True)
    
    print(f"Downloaded {len(df)} raw candles. Starting validation...")
    
    # Validate and clean data using DataValidator configured for 1h candles
    # expected_interval_sec = 3600 (1 hour)
    validator = DataValidator(expected_interval_sec=3600, window_size=100)
    cleaned_rows = []
    
    for idx, row in df.iterrows():
        tick_dict = {
            "timestamp": int(pd.to_datetime(row["time"]).timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"])
        }
        
        try:
            validated = validator.validate_and_filter(tick_dict)
            cleaned_rows.append(row)
        except DataGapError as e:
            # Plan: Forward-fill bounded gaps < 5 hours.
            # Convert timestamp diff to hours
            if validator.last_timestamp is not None:
                gap_hours = (tick_dict["timestamp"] - validator.last_timestamp) / 3600000.0
                if gap_hours <= 5:
                    print(f"Warning: Small data gap of {gap_hours:.1f} hours detected at {row['time']}. Forward-filling...")
                    # Generate missing candles
                    last_time = pd.to_datetime(validator.last_timestamp, unit='ms')
                    current_time = pd.to_datetime(tick_dict["timestamp"], unit='ms')
                    
                    # Get last valid row to fill with
                    last_valid_row = cleaned_rows[-1] if cleaned_rows else row
                    
                    # Fill missing intervals
                    missing_times = pd.date_range(start=last_time + pd.Timedelta(hours=1), end=current_time - pd.Timedelta(hours=1), freq='1h')
                    for m_time in missing_times:
                        fill_row = last_valid_row.copy()
                        fill_row['time'] = m_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                        cleaned_rows.append(fill_row)
                    
                    # Reset last_timestamp to enable validator to continue
                    validator.last_timestamp = tick_dict["timestamp"]
                    cleaned_rows.append(row)
                else:
                    print(f"Critical Error: Large gap of {gap_hours:.1f} hours detected at {row['time']}. Cannot forward-fill.")
                    raise e
            else:
                raise e
        except OutlierError as e:
            print(f"Warning: {e} - Skipping outlier tick at {row['time']}.")
            # Skip this row and don't append to cleaned_rows
            
    df_cleaned = pd.DataFrame(cleaned_rows).reset_index(drop=True)
    df_cleaned.to_parquet(output_path, index=False)
    print(f"Validation complete. Cleaned dataset contains {len(df_cleaned)} candles saved to {output_path}")

if __name__ == "__main__":
    download_historical_data()
