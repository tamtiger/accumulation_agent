import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

class GBMSimulator:
    """
    Geometric Brownian Motion simulator with regime-switching volatility.
    Regime parameters define the drift and volatility of the asset returns.
    """
    def __init__(self, initial_price: float = 30000.0, random_state: int = 42):
        self.initial_price = initial_price
        np.random.seed(random_state)
        
        # Regime definition: (drift, volatility)
        self.regime_params = {
            0: (-0.05, 0.80), # Panic Dump (negative drift, extreme vol)
            1: (0.00, 0.20),  # Sideways (zero drift, low vol)
            2: (0.05, 0.35),  # Bull Trend (positive drift, medium vol)
            3: (0.10, 0.70),  # Blowoff Top (high drift, high vol)
            4: (-0.02, 0.40)  # Bear Market (negative drift, medium vol)
        }

    def generate(self, regime_sequence: np.ndarray, dt: float = 1.0 / 365.0) -> pd.DataFrame:
        """
        Generates simulated prices and volumes based on a sequence of regime states.
        """
        n_steps = len(regime_sequence)
        prices = np.zeros(n_steps + 1)
        prices[0] = self.initial_price
        
        returns = np.zeros(n_steps)
        volumes = np.zeros(n_steps)
        
        for t in range(n_steps):
            regime = int(regime_sequence[t])
            mu, sigma = self.regime_params.get(regime, (0.0, 0.2))
            
            # Generate return
            z = np.random.normal()
            ret = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
            returns[t] = ret
            prices[t+1] = prices[t] * np.exp(ret)
            
            # Volume correlates with volatility
            base_vol = 100.0
            volumes[t] = max(10.0, np.random.normal(base_vol * (1.0 + sigma * 2.0), base_vol * 0.3))
            
        df = pd.DataFrame({
            "close": prices[1:],
            "returns": returns,
            "volume": volumes,
            "regime": regime_sequence
        })
        return df

class MSARGenerator:
    """
    Markov-switching Autoregressive (MS-AR) process generator.
    Models volatility clustering and fat tails.
    """
    def __init__(self, random_state: int = 42):
        np.random.seed(random_state)
        # Transition matrix for 3 macro regimes: Bear, Sideways, Bull
        self.trans_matrix = np.array([
            [0.85, 0.10, 0.05], # Bear
            [0.05, 0.90, 0.05], # Sideways
            [0.05, 0.10, 0.85]  # Bull
        ])
        # AR(1) coefficients per regime
        self.ar_coefs = {0: 0.1, 1: 0.0, 2: 0.2}
        # Volatilities per regime
        self.vols = {0: 0.04, 1: 0.015, 2: 0.025}
        # Constants per regime
        self.consts = {0: -0.002, 1: 0.0, 2: 0.003}

    def generate(self, n_steps: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates simulated returns and regime indices.
        """
        regimes = np.zeros(n_steps, dtype=int)
        returns = np.zeros(n_steps)
        
        # Initial regime
        current_state = 1
        regimes[0] = current_state
        returns[0] = np.random.normal(0, self.vols[current_state])
        
        for t in range(1, n_steps):
            # Transition
            p = self.trans_matrix[current_state]
            current_state = np.random.choice([0, 1, 2], p=p)
            regimes[t] = current_state
            
            # AR(1) return generation
            epsilon = np.random.normal(0, self.vols[current_state])
            returns[t] = self.consts[current_state] + self.ar_coefs[current_state] * returns[t-1] + epsilon
            
        return returns, regimes

class StylizedFactsValidator:
    """
    Validates whether a generated return series satisfies stylized market facts:
    1. Fat tails (kurtosis > 3.0)
    2. Volatility clustering (autocorrelation of absolute returns is positive and slowly decaying)
    """
    @staticmethod
    def validate_fat_tails(returns: np.ndarray) -> Dict[str, Any]:
        mean = np.mean(returns)
        std = np.std(returns)
        kurtosis = np.mean(((returns - mean) / std) ** 4)
        return {
            "kurtosis": float(kurtosis),
            "is_fat_tailed": bool(kurtosis > 3.0)
        }

    @staticmethod
    def validate_volatility_clustering(returns: np.ndarray, lags: int = 5) -> Dict[str, Any]:
        abs_ret = np.abs(returns - np.mean(returns))
        # Calculate autocorrelation at various lags
        autocorrs = []
        for lag in range(1, lags + 1):
            corr = np.corrcoef(abs_ret[:-lag], abs_ret[lag:])[0, 1]
            autocorrs.append(corr)
            
        mean_autocorr = float(np.mean(autocorrs))
        return {
            "autocorrelations": [float(c) for c in autocorrs],
            "volatility_clustering_detected": bool(mean_autocorr > 0.05)
        }
