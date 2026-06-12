import numpy as np
import math

class BOCPD:
    """
    Bayesian Online Change-Point Detection (BOCPD).
    Uses a Normal-Gamma conjugate prior for Gaussian observations.
    """
    def __init__(
        self,
        hazard: float = 1.0 / 250.0,  # Expected run length is 250 ticks
        mu_0: float = 0.0,
        kappa_0: float = 1.0,
        alpha_0: float = 1.0,
        beta_0: float = 1.0
    ):
        self.hazard = hazard
        self.mu_0 = mu_0
        self.kappa_0 = kappa_0
        self.alpha_0 = alpha_0
        self.beta_0 = beta_0
        
        # Initialize priors
        self.mu_t = np.array([mu_0])
        self.kappa_t = np.array([kappa_0])
        self.alpha_t = np.array([alpha_0])
        self.beta_t = np.array([beta_0])
        
        # Initial run length distribution
        self.R = np.array([1.0])
        self.t = 0

    def update(self, x: float) -> np.ndarray:
        """
        Update run-length distribution with a new observation.
        Returns the normalized run-length distribution array.
        """
        self.t += 1
        
        # 1. Compute predictive probability (Student-t distribution)
        dof = 2 * self.alpha_t
        scale = np.sqrt(self.beta_t * (self.kappa_t + 1) / (self.alpha_t * self.kappa_t))
        
        # Evaluate Student-t log PDF
        np_loggamma = np.vectorize(math.lgamma)
        t_stat = (x - self.mu_t) / scale
        log_pdf = (np_loggamma((dof + 1) / 2.0) - np_loggamma(dof / 2.0) - 
                   0.5 * np.log(np.pi * dof) - np.log(scale) - 
                   0.5 * (dof + 1) * np.log(1.0 + (t_stat ** 2) / dof))
        pred_probs = np.exp(log_pdf)
        
        # 2. Calculate growth probabilities and change-point probabilities
        # H(r) = hazard constant
        pc_growth = self.R * pred_probs * (1.0 - self.hazard)
        pc_change = pred_probs[0] * np.sum(self.R * self.hazard)
        
        # 3. Form the new run-length distribution
        new_R = np.zeros(self.t + 1)
        new_R[0] = pc_change
        new_R[1:] = pc_growth
        
        # Normalize
        self.R = new_R / np.sum(new_R)
        
        # 4. Update hyperparameters for all possible run lengths
        new_mu = (self.kappa_t * self.mu_t + x) / (self.kappa_t + 1)
        new_kappa = self.kappa_t + 1
        new_alpha = self.alpha_t + 0.5
        new_beta = self.beta_t + 0.5 * self.kappa_t * ((x - self.mu_t) ** 2) / (self.kappa_t + 1)
        
        # Prepend the priors for the new run-length of 0
        self.mu_t = np.insert(new_mu, 0, self.mu_0)
        self.kappa_t = np.insert(new_kappa, 0, self.kappa_0)
        self.alpha_t = np.insert(new_alpha, 0, self.alpha_0)
        self.beta_t = np.insert(new_beta, 0, self.beta_0)
        
        # Truncate arrays to prevent memory leak
        max_size = 500
        if len(self.R) > max_size:
            self.R = self.R[:max_size]
            self.R = self.R / np.sum(self.R)
            self.mu_t = self.mu_t[:max_size]
            self.kappa_t = self.kappa_t[:max_size]
            self.alpha_t = self.alpha_t[:max_size]
            self.beta_t = self.beta_t[:max_size]
            self.t = max_size - 1

        return self.R

    def get_change_probability(self) -> float:
        """
        Returns the probability that a change point occurred at the current tick (run-length = 0).
        """
        return float(self.R[0])
