import numpy as np
from typing import Optional

class NumPyKMeans:
    """
    A pure NumPy implementation of the K-Means clustering algorithm.
    """
    def __init__(self, n_clusters: int = 5, max_iter: int = 300, random_state: Optional[int] = None):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.random_state = random_state
        self.centroids = None

    def fit(self, X: np.ndarray, tol: float = 1e-4) -> "NumPyKMeans":
        if self.random_state is not None:
            np.random.seed(self.random_state)
            
        n_samples, n_features = X.shape
        
        # Initialize centroids randomly choosing points
        indices = np.random.choice(n_samples, self.n_clusters, replace=False)
        self.centroids = X[indices].copy()
        
        for iteration in range(self.max_iter):
            # Compute Euclidean distances from each point to each centroid
            # Shape: (n_samples, n_clusters)
            distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
            
            # Assign points to closest centroid
            labels = np.argmin(distances, axis=1)
            
            # Compute new centroids
            new_centroids = np.zeros_like(self.centroids)
            for k in range(self.n_clusters):
                points_in_cluster = X[labels == k]
                if len(points_in_cluster) > 0:
                    new_centroids[k] = np.mean(points_in_cluster, axis=0)
                else:
                    # If cluster is empty, reinitialize to a random point
                    new_centroids[k] = X[np.random.choice(n_samples)]
            
            # Check for convergence
            centroid_shift = np.sum(np.abs(self.centroids - new_centroids))
            self.centroids = new_centroids
            
            if centroid_shift < tol:
                break
                
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.centroids is None:
            raise ValueError("K-Means model is not fitted yet.")
            
        if len(X.shape) == 1:
            X = X.reshape(-1, 1)
            
        # Compute distances and assign closest cluster labels
        distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
        return np.argmin(distances, axis=1)
