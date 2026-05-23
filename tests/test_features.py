import pandas as pd
import numpy as np
from src.features.engine import FeatureEngine

def test_feature_calculations():
    # Construct a dummy DataFrame of 50 days (with hourly rows, 50 * 24 = 1200 rows)
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=1200, freq="h")
    
    # Generate prices with a random walk + upward trend
    prices = 30000.0 + np.cumsum(np.random.normal(5, 50, 1200))
    highs = prices + np.random.uniform(10, 100, 1200)
    lows = prices - np.random.uniform(10, 100, 1200)
    opens = prices - np.random.uniform(-50, 50, 1200)
    volumes = np.random.uniform(50, 500, 1200)
    funding_rates = np.random.uniform(-0.0002, 0.0004, 1200)
    open_interests = 100000.0 + np.cumsum(np.random.normal(10, 500, 1200))
    liquidations = np.random.choice([0.0, 10.0, 50.0], size=1200, p=[0.9, 0.08, 0.02])

    df = pd.DataFrame({
        "time": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
        "funding_rate": funding_rates,
        "open_interest": open_interests,
        "liquidations": liquidations
    })

    # Run features calculations
    df_feat = FeatureEngine.calculate_anchors_and_features(df)

    # Verify that anchors exist and are calculated
    assert "A_trend" in df_feat.columns
    assert "A_range" in df_feat.columns
    assert "sigma_ann" in df_feat.columns
    assert "A_vol" in df_feat.columns
    assert "A_mean" in df_feat.columns
    assert "rsi" in df_feat.columns
    assert "volume_zscore" in df_feat.columns
    assert "funding_rate_delta_24h" in df_feat.columns
    assert "open_interest_delta_24h" in df_feat.columns
    assert "liquidation_intensity" in df_feat.columns

    # Check bounds
    assert not df_feat["A_trend"].isna().any()
    assert not df_feat["A_range"].isna().any()
    assert not df_feat["sigma_ann"].isna().any()
    
    # Assert trend anchor is reasonably close to prices
    assert df_feat["A_trend"].iloc[-1] > 0
