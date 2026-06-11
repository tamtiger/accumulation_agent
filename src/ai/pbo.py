import numpy as np

class PBOEvaluator:
    """
    Computes the Probability of Backtest Overfitting (PBO) using combinatorial folds.
    Evaluates performance metrics of parameter trials across training and testing segments.
    """
    def __init__(self, n_segments: int = 6):
        self.n_segments = n_segments

    def compute_pbo(self, trials_performance: np.ndarray) -> float:
        """
        Computes PBO using a Combinatorial Cross Validation approach.
        Args:
            trials_performance: shape (n_trials, n_segments) containing the metric (e.g. Sharpe)
                                for each parameter combination across the N segments.
        Returns:
            pbo: float (0.0 to 1.0)
        """
        n_trials, n_seg = trials_performance.shape
        if n_seg != self.n_segments:
            raise ValueError(f"Performance matrix must have {self.n_segments} columns (segments).")
            
        # Generate all combinations of picking N/2 segments for test set
        test_size = n_seg // 2
        import itertools
        all_indices = list(range(n_seg))
        comb_test_indices = list(itertools.combinations(all_indices, test_size))
        
        overfit_count = 0
        total_folds = len(comb_test_indices)
        
        for test_idx in comb_test_indices:
            test_idx = list(test_idx)
            train_idx = [i for i in all_indices if i not in test_idx]
            
            # Compute In-Sample (IS) average performance for each trial
            is_performance = np.mean(trials_performance[:, train_idx], axis=1)
            
            # Identify the best trial IS
            best_trial_is = np.argmax(is_performance)
            
            # Compute Out-of-Sample (OOS) performance for all trials
            oos_performance = np.mean(trials_performance[:, test_idx], axis=1)
            
            # Calculate rank of the IS-best trial in OOS performance
            # Rank is computed as the fraction of trials that perform worse than the best IS trial
            oos_rank = np.sum(oos_performance < oos_performance[best_trial_is]) / (n_trials - 1)
            
            # If the best IS trial ranks in the lower half of OOS trials (rank < 0.5), it is overfit
            if oos_rank < 0.5:
                overfit_count += 1
                
        pbo = overfit_count / total_folds
        return pbo
