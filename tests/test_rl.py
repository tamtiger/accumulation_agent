import numpy as np
import pandas as pd
from src.ai.env import ABASGymEnv
from src.ai.rl_agent import NumPyRLAgent
from src.ai.pbo import PBOEvaluator

def test_abas_gym_env():
    # Setup dummy features dataframe
    np.random.seed(42)
    n_steps = 100
    df = pd.DataFrame({
        "close": np.linspace(30000, 31000, n_steps),
        "returns": np.random.normal(0.0001, 0.01, n_steps),
        "sigma_ann": np.full(n_steps, 0.30),
        "volume": np.random.normal(100, 10, n_steps),
        "regime": np.random.choice([0, 1, 2, 3, 4], n_steps),
        "A_range": np.full(n_steps, 31000.0)
    })
    
    # Pre-calculate rolling features so env.py has them
    df["returns_24h"] = df["returns"].rolling(24).sum().fillna(0.0)
    df["returns_7d"] = df["returns"].rolling(168).sum().fillna(0.0)
    
    env = ABASGymEnv(df, initial_reserve_usdt=100000.0)
    state = env.reset()
    
    assert state.shape == (21,)
    
    # Step environment
    action = np.array([1.0, 1.0, 1.0, 1.0])
    next_state, reward, done, info = env.step(action)
    
    assert next_state.shape == (21,)
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert "portfolio_value_usdt" in info

def test_numpy_rl_agent():
    state_dim = 21
    action_dim = 4
    agent = NumPyRLAgent(state_dim=state_dim, action_dim=action_dim, learning_rate=0.1)
    
    state = np.random.normal(0, 1, state_dim)
    action, means = agent.get_action(state, train=True)
    
    assert action.shape == (action_dim,)
    assert means.shape == (action_dim,)
    assert np.all(action >= 0.5) and np.all(action <= 1.5)
    
    # Train test
    states = [state, state]
    actions = [action, action]
    means_history = [means, means]
    rewards = [1.0, 2.0]
    
    loss = agent.train_episode(states, actions, means_history, rewards)
    assert isinstance(loss, float)

def test_pbo_evaluator():
    evaluator = PBOEvaluator(n_segments=4)
    
    # Setup trials performance matrix: 3 trials, 4 segments
    # Trial 0 is best in segment 0, 1 but worst in 2, 3 (overfit)
    # Trial 1 is stable
    # Trial 2 is stable
    trials_perf = np.array([
        [10.0, 10.0, -5.0, -5.0], # overfits IS segments 0, 1
        [1.0, 1.0, 1.0, 1.0],
        [0.5, 0.5, 0.5, 0.5]
    ])
    
    pbo = evaluator.compute_pbo(trials_perf)
    assert 0.0 <= pbo <= 1.0
