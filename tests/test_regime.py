import numpy as np
import pytest
from src.regime.hmm import GaussianHMM
from src.regime.kmeans import NumPyKMeans
from src.regime.bocpd import BOCPD
from src.regime.classifier import RegimeClassifier

def test_gaussian_hmm():
    # Generate synthetic data from 2 states (1D)
    np.random.seed(42)
    x1 = np.random.normal(loc=-1.0, scale=0.2, size=100)
    x2 = np.random.normal(loc=1.0, scale=0.2, size=100)
    X = np.concatenate([x1, x2]).reshape(-1, 1)
    
    hmm = GaussianHMM(n_components=2, random_state=42)
    hmm.fit(X)
    
    # Assert means are learned close to -1.0 and 1.0
    sorted_means = np.sort(hmm.means_, axis=0)
    assert pytest.approx(sorted_means[0, 0], abs=0.3) == -1.0
    assert pytest.approx(sorted_means[1, 0], abs=0.3) == 1.0
    
    # Assert Viterbi decoding assigns correct states
    states = hmm.predict(X)
    assert len(states) == 200
    # First 100 should mostly have the same state, last 100 should have the other
    assert len(np.unique(states[:100])) == 1
    assert len(np.unique(states[100:])) == 1
    assert states[0] != states[100]
    
    # Test scoring/log-likelihood
    score = hmm.score(X)
    assert isinstance(score, float)
    assert not np.isnan(score)

def test_numpy_kmeans():
    np.random.seed(42)
    x1 = np.random.normal(loc=[-2.0, -2.0], scale=0.5, size=(50, 2))
    x2 = np.random.normal(loc=[2.0, 2.0], scale=0.5, size=(50, 2))
    X = np.concatenate([x1, x2])
    
    kmeans = NumPyKMeans(n_clusters=2, random_state=42)
    kmeans.fit(X)
    
    # Centroids should be close to [-2, -2] and [2, 2]
    sorted_centroids = sorted(kmeans.centroids.tolist())
    assert pytest.approx(sorted_centroids[0][0], abs=0.5) == -2.0
    assert pytest.approx(sorted_centroids[1][0], abs=0.5) == 2.0
    
    # Prediction test
    labels = kmeans.predict(X)
    assert len(labels) == 100
    assert np.all(labels[:50] == labels[0])
    assert np.all(labels[50:] == labels[50])
    assert labels[0] != labels[50]

def test_bocpd():
    # Constant data followed by a sudden jump
    data = np.concatenate([np.zeros(20), np.ones(20) * 10.0])
    bocpd = BOCPD(hazard=0.01)
    
    change_probabilities = []
    for x in data:
        bocpd.update(x)
        change_probabilities.append(bocpd.get_change_probability())
        
    # Before change-point, probability of change (r=0) should be low
    assert change_probabilities[5] < 0.1
    # Right after the jump at index 20, the change probability should spike
    assert change_probabilities[20] > 0.5

def test_regime_classifier_hysteresis():
    classifier = RegimeClassifier(n_components=2)
    classifier.hmm_mapping = {0: 1, 1: 2} # Map raw state 0 -> 1 (Sideways), 1 -> 2 (Bull Trend)
    classifier.is_fitted = True
    
    # Mock HMM predict and _pdf
    class MockHMM:
        def predict(self, X):
            # First tick returns state 1 (mapped to 2), next returns 0 (mapped to 1)
            return np.array([self.state])
        def _pdf(self, X):
            # Mock confidence
            return np.array([[0.1, 0.9]]) if self.state == 1 else np.array([[0.8, 0.2]])
            
    mock_hmm = MockHMM()
    classifier.hmm = mock_hmm
    
    # Start in Sideways (1)
    classifier.current_regime = 1
    
    # 1. Propose change to Bull Trend (2) with low confidence (0.9 < 0.95)
    mock_hmm.state = 1 # raw state 1 -> regime 2
    # Conf: 0.9 / 1.0 = 0.9
    res = classifier.predict_tick({"close": 100.0, "sigma_ann": 0.2})
    assert res["regime"] == 1  # No transition yet (hysteresis)
    assert classifier.pending_count == 1
    
    # Confirming candle 2
    res = classifier.predict_tick({"close": 100.0, "sigma_ann": 0.2})
    assert res["regime"] == 1  # No transition yet (hysteresis)
    assert classifier.pending_count == 2
    
    # Confirming candle 3 -> Transitions!
    res = classifier.predict_tick({"close": 100.0, "sigma_ann": 0.2})
    assert res["regime"] == 2
    assert classifier.pending_count == 0
    
    # 2. Instant transition test with high confidence
    classifier.current_regime = 2
    mock_hmm.state = 0 # raw state 0 -> regime 1
    # Mock high confidence
    mock_hmm._pdf = lambda X: np.array([[0.99, 0.01]])
    # Conf: 0.99 / 1.0 = 0.99 > 0.95
    res = classifier.predict_tick({"close": 100.0, "sigma_ann": 0.2})
    assert res["regime"] == 1  # Instant transition
    assert classifier.pending_count == 0
