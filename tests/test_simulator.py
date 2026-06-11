import numpy as np
from src.simulator.market_sim import GBMSimulator, MSARGenerator, StylizedFactsValidator

def test_gbm_simulator():
    sim = GBMSimulator(initial_price=30000.0, random_state=42)
    regimes = np.array([1, 1, 2, 2, 0, 0, 3, 3, 4, 4])
    
    df = sim.generate(regimes)
    assert len(df) == 10
    assert "close" in df
    assert "volume" in df
    assert "regime" in df
    assert df.loc[0, "regime"] == 1
    assert df.loc[9, "regime"] == 4

def test_msar_generator_and_validator():
    gen = MSARGenerator(random_state=42)
    returns, regimes = gen.generate(100)
    
    assert len(returns) == 100
    assert len(regimes) == 100
    
    # Generate long series to validate stylized facts
    long_returns, _ = gen.generate(1000)
    
    fat_tails = StylizedFactsValidator.validate_fat_tails(long_returns)
    assert "kurtosis" in fat_tails
    assert "is_fat_tailed" in fat_tails
    
    vol_clustering = StylizedFactsValidator.validate_volatility_clustering(long_returns)
    assert "autocorrelations" in vol_clustering
    assert "volatility_clustering_detected" in vol_clustering
