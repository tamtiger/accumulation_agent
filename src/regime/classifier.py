import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.regime.hmm import GaussianHMM
from src.regime.kmeans import NumPyKMeans
from src.regime.bocpd import BOCPD
from src.utils.db import get_connection, release_connection
from src.utils.logging import get_agent_logger

logger = get_agent_logger("regime_classifier")

class RegimeClassifier:
    """
    Coordinates unsupervised HMM, K-Means, and BOCPD models to classify
    market regimes and map them post-hoc to 5 target semantic regimes:
    0: Panic Dump, 1: Sideways, 2: Bull Trend, 3: Blowoff Top, 4: Bear Market
    """
    def __init__(self, n_components: int = 5):
        self.n_components = n_components
        self.hmm = GaussianHMM(n_components=n_components, random_state=42)
        self.kmeans = NumPyKMeans(n_clusters=n_components, random_state=42)
        self.bocpd = BOCPD()
        
        # State mapping dictionary: cluster/state index -> semantic regime index (0-4)
        self.hmm_mapping: Dict[int, int] = {}
        self.kmeans_mapping: Dict[int, int] = {}
        
        self.is_fitted = False
        
        # Hysteresis state tracking
        self.current_regime: int = 1  # Sideways default
        self.pending_regime: Optional[int] = None
        self.pending_count: int = 0

    def fit_from_db(self, limit: int = 1000) -> None:
        """
        Loads historical features from DB and fits HMM and K-Means.
        """
        logger.info(f"Loading historical features for training Regime Classifier (limit={limit})...")
        conn = get_connection()
        try:
            # We want to select historical data with features
            # Let's fetch latest data from binance_ohlcv and joint features
            # Note: We need a DataFrame with daily log returns, realized volatility, EMA slopes, RSI, volume z-score, etc.
            # If not enough records, we will use synthetic/fallback values to fit.
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT close, volume, time 
                    FROM binance_ohlcv 
                    ORDER BY time DESC 
                    LIMIT %s
                    """,
                    (limit,)
                )
                rows = cur.fetchall()
            
            if len(rows) < 50:
                logger.warning("Too few database records to fit regime models. Using baseline identity mapping.")
                self._set_baseline_mapping()
                return
                
            df = pd.DataFrame(rows, columns=["close", "volume", "time"]).iloc[::-1].reset_index(drop=True)
            df["returns"] = np.log(df["close"] / df["close"].shift(1))
            df["returns"] = df["returns"].fillna(0.0)
            df["vol"] = df["returns"].rolling(window=30).std() * np.sqrt(365)
            df["vol"] = df["vol"].fillna(df["returns"].std() * np.sqrt(365))
            
            # Simple technical indicators for K-Means
            df["volume_z"] = (df["volume"] - df["volume"].rolling(window=30).mean()) / df["volume"].rolling(window=30).std().fillna(1.0)
            df["volume_z"] = df["volume_z"].fillna(0.0)
            
            # Feature matrices
            # X_hmm uses [returns, vol]
            X_hmm = df[["returns", "vol"]].to_numpy()
            self.hmm.fit(X_hmm)
            
            # X_kmeans uses [returns, vol, volume_z]
            X_kmeans = df[["returns", "vol", "volume_z"]].to_numpy()
            self.kmeans.fit(X_kmeans)
            
            # Run post-hoc centroid analysis to build semantic mappings
            self._build_semantic_mappings(X_hmm, X_kmeans)
            self.is_fitted = True
            logger.info("Regime Classifier successfully trained and post-hoc mapped.")
            
        except Exception as e:
            logger.error(f"Failed to fit Regime Classifier: {e}. Falling back to baseline mapping.")
            self._set_baseline_mapping()
        finally:
            release_connection(conn)

    def _set_baseline_mapping(self) -> None:
        # If training fails, use identity mappings
        self.hmm_mapping = {i: i % 5 for i in range(self.n_components)}
        self.kmeans_mapping = {i: i % 5 for i in range(self.n_components)}
        
        # Initialize dummy model parameters to support predict() calls in fallback mode
        self.hmm.means_ = np.zeros((self.n_components, 2))
        self.hmm.covars_ = np.ones((self.n_components, 2))
        self.hmm.startprob_ = np.full(self.n_components, 1.0 / self.n_components)
        self.hmm.transmat_ = np.full((self.n_components, self.n_components), 1.0 / self.n_components)
        
        self.kmeans.centroids = np.zeros((self.n_components, 3))
        
        self.is_fitted = True

    def _build_semantic_mappings(self, X_hmm: np.ndarray, X_kmeans: np.ndarray) -> None:
        """
        Maps cluster/state indices (0 to n-1) to semantic regimes (0 to 4):
        0: Panic Dump (negative returns, high vol, high volume)
        1: Sideways (low vol, near-zero returns)
        2: Bull Trend (positive returns, medium vol)
        3: Blowoff Top (very high positive returns, very high vol)
        4: Bear Market (negative returns, medium/low vol)
        """
        # 1. Map HMM States
        hmm_states = self.hmm.predict(X_hmm)
        hmm_centroids = []
        for i in range(self.n_components):
            mask = (hmm_states == i)
            if np.any(mask):
                hmm_centroids.append({
                    "index": i,
                    "returns": np.mean(X_hmm[mask, 0]),
                    "vol": np.mean(X_hmm[mask, 1])
                })
            else:
                hmm_centroids.append({
                    "index": i,
                    "returns": 0.0,
                    "vol": 1.0
                })
                
        # Sort states by volatility
        sorted_by_vol = sorted(hmm_centroids, key=lambda x: x["vol"])
        
        # Map lowest volatility to Sideways (1)
        self.hmm_mapping[sorted_by_vol[0]["index"]] = 1
        
        # Map highest volatility
        highest_vol = sorted_by_vol[-1]
        if highest_vol["returns"] < 0:
            self.hmm_mapping[highest_vol["index"]] = 0  # Panic Dump
        else:
            self.hmm_mapping[highest_vol["index"]] = 3  # Blowoff Top
            
        # Map second highest volatility
        sec_highest_vol = sorted_by_vol[-2]
        if sec_highest_vol["index"] not in self.hmm_mapping:
            if sec_highest_vol["returns"] < 0:
                self.hmm_mapping[sec_highest_vol["index"]] = 4  # Bear Market
            else:
                self.hmm_mapping[sec_highest_vol["index"]] = 2  # Bull Trend
                
        # Fill remaining states based on returns
        for item in sorted_by_vol:
            idx = item["index"]
            if idx not in self.hmm_mapping:
                if item["returns"] > 0:
                    self.hmm_mapping[idx] = 2  # Bull Trend
                else:
                    self.hmm_mapping[idx] = 4  # Bear Market
                    
        # 2. Map K-Means clusters (centroids is of shape (n_clusters, n_features))
        for i in range(self.n_components):
            centroid = self.kmeans.centroids[i]
            ret_val = centroid[0]
            vol_val = centroid[1]
            
            # Simple threshold logic for K-means centroids
            if vol_val < 0.15:
                self.kmeans_mapping[i] = 1  # Sideways
            elif vol_val > 0.40:
                if ret_val < 0:
                    self.kmeans_mapping[i] = 0  # Panic Dump
                else:
                    self.kmeans_mapping[i] = 3  # Blowoff Top
            else:
                if ret_val > 0:
                    self.kmeans_mapping[i] = 2  # Bull Trend
                else:
                    self.kmeans_mapping[i] = 4  # Bear Market

    def predict_tick(self, latest_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies current market tick and applies hysteresis.
        Returns:
            dict containing:
                "regime": int (0-4)
                "confidence": float (0.0 to 1.0)
                "change_probability": float (BOCPD change metric)
        """
        if not self.is_fitted:
            self.fit_from_db()
            
        # Extract features
        float(latest_features["close"])
        returns = float(latest_features.get("returns_24h", 0.0))
        vol = float(latest_features["sigma_ann"])
        
        # 1. Run BOCPD update with returns
        self.bocpd.update(returns)
        change_prob = self.bocpd.get_change_probability()
        
        # 2. Predict HMM state using current sample [returns, vol]
        sample = np.array([[returns, vol]])
        raw_hmm_state = int(self.hmm.predict(sample)[0])
        mapped_hmm_regime = self.hmm_mapping.get(raw_hmm_state, 1)
        
        # Estimate HMM posterior probability/confidence
        # Let's compute probability density of all states
        pdf_vals = self.hmm._pdf(sample)[0]
        pdf_sum = np.sum(pdf_vals)
        confidence = float(pdf_vals[raw_hmm_state] / pdf_sum if pdf_sum > 0 else 1.0)
        
        # 3. Apply Hysteresis Filtering
        # Requires 3 consecutive confirmations or confidence > 0.95 to switch states
        proposed_regime = mapped_hmm_regime
        
        if proposed_regime == self.current_regime:
            self.pending_regime = None
            self.pending_count = 0
        else:
            if confidence > 0.95:
                # Instant transition
                self.current_regime = proposed_regime
                self.pending_regime = None
                self.pending_count = 0
            else:
                if self.pending_regime == proposed_regime:
                    self.pending_count += 1
                    if self.pending_count >= 3:
                        self.current_regime = proposed_regime
                        self.pending_regime = None
                        self.pending_count = 0
                else:
                    self.pending_regime = proposed_regime
                    self.pending_count = 1
                    
        return {
            "regime": self.current_regime,
            "confidence": confidence,
            "change_probability": change_prob
        }
