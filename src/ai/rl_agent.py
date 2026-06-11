import numpy as np
from typing import List, Tuple

class NumPyRLAgent:
    """
    A pure NumPy implementation of a Policy Gradient (REINFORCE) agent.
     Learns a parameterized policy mapping state vectors to continuous actions.
    """
    def __init__(self, state_dim: int, action_dim: int, learning_rate: float = 0.01, gamma: float = 0.99):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = learning_rate
        self.gamma = gamma
        
        # Policy parameters: linear weights mapping state to action means
        # Initialized to near-zero to produce actions around the default 1.0 (mean of sigmoid is 0.5 + 0.5 = 1.0)
        self.W = np.random.normal(0, 0.01, (action_dim, state_dim))
        self.sigma = 0.15 # Exploration standard deviation

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))

    def get_action(self, state: np.ndarray, train: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes action and its probability distribution.
        Returns:
            action: shape (action_dim,) bounded in [0.5, 1.5]
            mean: shape (action_dim,)
        """
        # Linear layer + Sigmoid mapping to [0, 1] then shifted to [0.5, 1.5]
        raw_out = np.dot(self.W, state)
        means = self._sigmoid(raw_out) + 0.5
        
        if train:
            # Sample action from Gaussian distribution
            action = np.random.normal(means, self.sigma)
        else:
            action = means
            
        action = np.clip(action, 0.5, 1.5)
        return action, means

    def train_episode(self, states: List[np.ndarray], actions: List[np.ndarray], means: List[np.ndarray], rewards: List[float]) -> float:
        """
        Updates policy parameters using REINFORCE gradient ascent.
        """
        episode_length = len(rewards)
        discounted_rewards = np.zeros(episode_length)
        
        # Calculate discounted returns (rewards-to-go)
        running_add = 0.0
        for t in reversed(range(episode_length)):
            running_add = rewards[t] + self.gamma * running_add
            discounted_rewards[t] = running_add
            
        # Standardize returns to reduce variance
        if len(discounted_rewards) > 1:
            mean_ret = np.mean(discounted_rewards)
            std_ret = np.std(discounted_rewards)
            if std_ret > 1e-6:
                discounted_rewards = (discounted_rewards - mean_ret) / std_ret
                
        # Perform gradient updates
        total_loss = 0.0
        for t in range(episode_length):
            state = states[t]
            action = actions[t]
            mean = means[t]
            G = discounted_rewards[t]
            
            # Log-derivative of Gaussian distribution: d/dW log pi(a|s)
            # pi(a|s) ~ N(mean, sigma^2) where mean = sigmoid(W*s) + 0.5
            # d/dW mean = mean * (1 - mean) * s
            # d/dW log pi(a|s) = (a - mean) / (sigma^2) * d/dW mean
            #                  = (a - mean) / (sigma^2) * (mean - 0.5) * (1.5 - mean) * s
            
            # Note: mean is in [0.5, 1.5]. The underlying sigmoid is (mean - 0.5)
            sig = mean - 0.5
            grad_mean = sig * (1.0 - sig)
            
            for i in range(self.action_dim):
                diff = action[i] - mean[i]
                grad_w = (diff / (self.sigma ** 2)) * grad_mean[i] * state
                self.W[i] += self.lr * grad_w * G
                
            loss = 0.5 * np.sum(((action - mean) / self.sigma) ** 2)
            total_loss += loss
            
        return total_loss / episode_length

    def save(self, filepath: str) -> None:
        np.savez(filepath, W=self.W)

    def load(self, filepath: str) -> None:
        data = np.load(filepath)
        self.W = data["W"]
