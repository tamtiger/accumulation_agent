import numpy as np
from typing import Optional

class GaussianHMM:
    """
    A pure NumPy implementation of a Gaussian Hidden Markov Model (HMM).
    Supports diagonal covariance matrices and multi-dimensional observations.
    """
    def __init__(self, n_components: int = 3, random_state: Optional[int] = None):
        self.n_components = n_components
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)
            
        self.startprob_ = None
        self.transmat_ = None
        self.means_ = None
        self.covars_ = None

    def _init_params(self, X: np.ndarray) -> None:
        n_samples, n_features = X.shape
        
        # Initialize startprob uniformly
        self.startprob_ = np.full(self.n_components, 1.0 / self.n_components)
        
        # Initialize transmat with high self-transition probability (stable states)
        self.transmat_ = np.full((self.n_components, self.n_components), 0.1 / (self.n_components - 1))
        np.fill_diagonal(self.transmat_, 0.9)
        
        # Initialize means using random choice of data points
        indices = self.rng.choice(n_samples, self.n_components, replace=False)
        self.means_ = X[indices].copy()
        
        # Initialize covariances to variance of data
        var = np.var(X, axis=0)
        # Prevent 0 variance
        var[var < 1e-4] = 1e-4
        self.covars_ = np.tile(var, (self.n_components, 1))

    def _pdf(self, X: np.ndarray) -> np.ndarray:
        """
        Evaluate probability density function of states for each sample.
        Returns: array of shape (n_samples, n_components)
        """
        n_samples, n_features = X.shape
        probs = np.zeros((n_samples, self.n_components))
        
        for i in range(self.n_components):
            mean = self.means_[i]
            covar = self.covars_[i]
            
            # Diagonal Gaussian probability density
            diff = X - mean
            exponent = -0.5 * np.sum((diff ** 2) / covar, axis=1)
            norm_const = 1.0 / np.sqrt(((2 * np.pi) ** n_features) * np.prod(covar))
            probs[:, i] = norm_const * np.exp(exponent)
            
        # Clip to prevent exact zero probabilities
        probs = np.clip(probs, 1e-300, None)
        return probs

    def fit(self, X: np.ndarray, max_iter: int = 100, tol: float = 1e-4) -> "GaussianHMM":
        """
        Fit HMM parameters using Baum-Welch EM algorithm.
        """
        if len(X.shape) == 1:
            X = X.reshape(-1, 1)
            
        self._init_params(X)
        n_samples, n_features = X.shape
        
        old_log_likelihood = -np.inf
        
        for iteration in range(max_iter):
            # 1. Evaluate PDFs
            B = self._pdf(X)
            
            # 2. Forward-Backward with scaling to prevent underflow
            alpha = np.zeros((n_samples, self.n_components))
            c = np.zeros(n_samples) # scaling factors
            
            # Forward pass
            alpha[0] = self.startprob_ * B[0]
            c[0] = np.sum(alpha[0])
            alpha[0] /= c[0]
            
            for t in range(1, n_samples):
                alpha[t] = np.dot(alpha[t-1], self.transmat_) * B[t]
                c[t] = np.sum(alpha[t])
                alpha[t] /= c[t]
                
            log_likelihood = np.sum(np.log(c))
            
            # Convergence check
            if np.abs(log_likelihood - old_log_likelihood) < tol:
                break
            old_log_likelihood = log_likelihood
            
            # Backward pass
            beta = np.zeros((n_samples, self.n_components))
            beta[n_samples - 1] = 1.0
            
            for t in range(n_samples - 2, -1, -1):
                beta[t] = np.dot(self.transmat_, B[t+1] * beta[t+1]) / c[t+1]
                
            # 3. M-Step: Update parameters
            gamma = alpha * beta
            gamma /= np.sum(gamma, axis=1, keepdims=True)
            
            # Compute xi for transition matrix updates
            xi = np.zeros((n_samples - 1, self.n_components, self.n_components))
            for t in range(n_samples - 1):
                numerator = self.transmat_ * np.outer(alpha[t], B[t+1] * beta[t+1])
                denom = c[t+1]
                xi[t] = numerator / denom
                
            # Update startprob
            self.startprob_ = gamma[0] / np.sum(gamma[0])
            
            # Update transmat
            sum_xi = np.sum(xi, axis=0)
            sum_gamma_t = np.sum(gamma[:-1], axis=0, keepdims=True).T
            self.transmat_ = sum_xi / np.maximum(sum_gamma_t, 1e-12)
            # Normalize transition matrix
            self.transmat_ /= np.sum(self.transmat_, axis=1, keepdims=True)
            
            # Update means and covariances
            sum_gamma = np.sum(gamma, axis=0, keepdims=True).T
            self.means_ = np.dot(gamma.T, X) / np.maximum(sum_gamma, 1e-12)
            
            for i in range(self.n_components):
                diff = X - self.means_[i]
                self.covars_[i] = np.dot(gamma[:, i], diff ** 2) / np.maximum(sum_gamma[i, 0], 1e-12)
                # Keep diagonal covariances strictly positive
                self.covars_[i] = np.maximum(self.covars_[i], 1e-4)
                
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Viterbi algorithm to decode state sequence.
        """
        if len(X.shape) == 1:
            X = X.reshape(-1, 1)
            
        n_samples = X.shape[0]
        B = self._pdf(X)
        
        # log values to prevent underflow
        log_startprob = np.log(np.maximum(self.startprob_, 1e-300))
        log_transmat = np.log(np.maximum(self.transmat_, 1e-300))
        log_B = np.log(np.maximum(B, 1e-300))
        
        viterbi = np.zeros((n_samples, self.n_components))
        backpointer = np.zeros((n_samples, self.n_components), dtype=int)
        
        viterbi[0] = log_startprob + log_B[0]
        
        for t in range(1, n_samples):
            for j in range(self.n_components):
                trans_probs = viterbi[t-1] + log_transmat[:, j]
                backpointer[t, j] = np.argmax(trans_probs)
                viterbi[t, j] = trans_probs[backpointer[t, j]] + log_B[t, j]
                
        # Backtracking
        states = np.zeros(n_samples, dtype=int)
        states[-1] = np.argmax(viterbi[-1])
        
        for t in range(n_samples - 2, -1, -1):
            states[t] = backpointer[t+1, states[t+1]]
            
        return states

    def score(self, X: np.ndarray) -> float:
        """
        Calculate total log likelihood of observations.
        """
        if len(X.shape) == 1:
            X = X.reshape(-1, 1)
            
        n_samples = X.shape[0]
        B = self._pdf(X)
        
        alpha = np.zeros((n_samples, self.n_components))
        c = np.zeros(n_samples)
        
        alpha[0] = self.startprob_ * B[0]
        c[0] = np.sum(alpha[0])
        alpha[0] /= c[0]
        
        for t in range(1, n_samples):
            alpha[t] = np.dot(alpha[t-1], self.transmat_) * B[t]
            c[t] = np.sum(alpha[t])
            alpha[t] /= c[t]
            
        return float(np.sum(np.log(c)))
