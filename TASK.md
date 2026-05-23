# Implementation Task List (task.md)

This file tracks the implementation progress of the **Adaptive BTC Accumulation System (ABAS) — v2** across all development phases.

## Phase Progress Summary
*   [x] **Phase 0: Project Infrastructure** (100% Completed)
*   [x] **Phase 1: Rule-Based Prototype** (100% Completed)
*   [ ] **Phase 2: Historical Backtesting** (0% Completed)
*   [ ] **Phase 3: AI Overlay** (0% Completed)
*   [ ] **Phase 4: RL Optimization** (0% Completed)
*   [ ] **Phase 5: Paper Trading** (0% Completed)
*   [ ] **Phase 6: Small Capital Deployment** (0% Completed)
*   [ ] **Phase 7: Delta-Neutral Sleeve (Optional)** (0% Completed)

---

## Task Details

### Phase 0 — Project Infrastructure (Foundations)
- [x] **Repository Scaffolding (`src/`)**
    - [x] Create core directory structure (`data/`, `features/`, `regime/`, `inventory/`, `grid/`, `risk/`, `execution/`, `portfolio/`, `custody/`, `monitoring/`, `backtest/`, `simulator/`, `ai/`, `tests/`, `config/`).
- [x] **Python Environment Setup**
    - [x] Set up `pyproject.toml` or `requirements.txt` using the `uv` toolchain.
    - [x] Install required packages (ccxt, numpy, pandas, pydantic, sqlalchemy, psycopg2, redis, prometheus_client, pytest, hypothesis).
    - [x] Set up basic CI/CD pipeline template (GitHub Actions linter and test runner).
- [x] **Services & Infrastructure Deployment**
    - [x] Create `docker-compose.yml` to launch PostgreSQL/TimescaleDB and Redis locally.
    - [x] Initialize PostgreSQL schema with timescaledb extension enabled.
- [x] **Configuration Management (`src/config/`)**
    - [x] Implement `src/config.py` using Pydantic Settings to load and validate configurations from `config/production.json` and environmental variables.
    - [x] Add default values for all parameters (`reserve_floor`, `daily_deployment_cap`, `hot_exchange_cap`, `min_profit_threshold`, etc.).
- [x] **Logging System**
    - [x] Design a structured JSON logging system.
    - [x] Add redactor filters to scrub credentials, API keys, and sensitive database connection URLs.

### Phase 1 — Rule-Based Prototype (Core Engine)
> **Recommended Build Order:** `data/` → `features/` → `inventory/` → `grid/` → `risk/` → `execution/` → `portfolio/` → `custody/` → `monitoring/`

- [x] **Data Ingestion & Cleaning (`src/data/`)**
    - [x] Create Binance OHLCV, funding rate, and Open Interest ingesters via CCXT.
    - [x] Implement Gap Detection pipeline (flag, don't silently fill gaps).
    - [x] Implement Outlier Detection filter (rolling z-score).
    - [x] Write schema validations for incoming data streams.
    - [x] *Testing:* Unit test gap and outlier detection with synthetic bad records.
- [x] **Feature Engineering (`src/features/`)**
    - [x] Implement technical indicators: EMA slopes (EMA20, EMA50, EMA200), RSI(14), rolling volume z-scores, Open Interest delta, and funding rate delta.
    - [x] Implement rolling reference anchors calculations: $A_{\text{trend}}$, $A_{\text{range}}$, $A_{\text{vol}}$, $A_{\text{mean}}$.
    - [x] Implement 30-day annualized realized volatility $\sigma_{\text{ann}}$ from daily log returns for grid spacing calculations.
    - [x] *Testing:* Unit test anchors and indicator outputs against pre-calculated pandas test vectors.
- [x] **Inventory Engine (`src/inventory/`)**
    - [x] Create FIFO ledger for per-lot BTC tracking: `(qty, price, timestamp, regime_tag)`.
    - [x] Implement calculations for `avg_cost`, `realized_pnl_btc`, and `unrealized_pnl_btc`.
    - [x] Set up database models for portfolio state and transaction snapshots.
    - [x] *Testing:* Property-based tests (Hypothesis) validating FIFO balance preservation on buy/sell combos.
- [x] **Adaptive Grid Engine (`src/grid/`)**
    - [x] Code base deployment table logic ($3\%, 6\%, 10\%, 15\%, 25\%$ drawdowns from $A_{\text{range}}$).
    - [x] Create adaptive grid spacing calculations based on $\sigma_{\text{ann}}$ volatility thresholds.
    - [x] Implement sell-gating checks ensuring target price is $\ge A_{\text{cost}} \times (1 + \text{min\_profit\_threshold})$ and final trading sleeve remains $\ge$ `trading_floor`.
    - [x] *Testing:* Verify order limits generation across varying volatility regimes.
- [x] **Risk Overlay & Invariant Enforcement (`src/risk/`)**
    - [x] Implement invariant checks: `INV-1` to `INV-7` as hard assertions before submission.
    - [x] Implement Kill Switch triggers (drawdown, reserve floor, stablecoin depeg, spread).
    - [x] Code the automatic halt/freeze logic.
    - [x] *Testing:* Property-based tests (Hypothesis) ensuring orders violating `INV-1` or `INV-2` are rejected.
- [x] **Orchestrator & Execution Prototype (`src/execution/`)**
    - [x] Build the main loop orchestrating: Data Validation → Features → (Fallback Regime) → Inventory → Grid → Risk → Execution → Portfolio → Monitoring.
    - [x] Build basic CCXT mock environment for testing fills, partial fills, and slippage conversion.
    - [x] *Testing:* Run full loop with mockup data to verify tick-by-tick state persistence in TimescaleDB.
- [x] **Portfolio Tracking & Reconciliation (`src/portfolio/`)**
    - [x] Create portfolio tracker to verify and update balances.
    - [x] Build end-of-day reconciliation loop comparing database balances with mock exchange balances.
    - [x] *Testing:* Verify balance reconciliation outputs warnings if discrepancy $> 0.01\%$.
- [x] **Custody & Sweeping (`src/custody/`)**
    - [x] Code core promotion sweep signal logic (calculating excess when `trading_btc_qty > trading_target * 1.3` for 7 consecutive days).
    - [x] *Testing:* Verify sweep signal fires only after 7 continuous days of target breach.
- [x] **Monitoring & Alerting (`src/monitoring/`)**
    - [x] Register Prometheus gauges/counters for loops latency, order slippage, and balances.
    - [x] Implement Telegram notification wrapper.
    - [x] *Testing:* Trigger a mock halt and verify Telegram message dispatch.
- [x] **Backtest Harness (`src/backtest/`)**
    - [x] Set up Vectorbt/Backtrader backtesting framework.
    - [x] Integrate transaction fees (taker/maker), slippage models, and withdrawal fee assumptions.
    - [x] Implement tax drag model with after-tax reporting.
    - [x] *Testing:* Verify tax logic on long-term capital gains vs short-term rates.

### Phase 2 — Historical Backtesting & Validation
- [ ] **Cycle-by-Cycle Historical Simulation**
    - [ ] Run simulations for:
        - [ ] 2018–2019 (Bear + early recovery)
        - [ ] 2020–2021 (Bull market)
        - [ ] 2022 (Survival / Drawdown)
        - [ ] 2023 (Transition / Recovery)
        - [ ] 2024 (ETF flows)
- [ ] **Sensitivity Analyses**
    - [ ] Run parameter sweeps across fee levels ($0.05\% / 0.10\% / 0.15\%$).
    - [ ] Run parameter sweeps across slippage rates ($0.02\% / 0.05\% / 0.10\%$).
    - [ ] Run parameter sweeps across tax rates ($0\% / 20\% / 35\%$).
- [ ] **Benchmark Reporting**
    - [ ] Generate reports showing performance vs. HODL, weekly DCA, and fixed 5% grid.
    - [ ] Calculate BTC-native metrics: `Δ_BTC vs HODL`, BTC CAGR, BTC velocity, Max Drawdown.
    - [ ] *Testing:* Verify backtest determinism (running identical backtest twice yields identical results).

### Phase 3 — AI Overlay (Regime Detection)
- [ ] **Advanced Features & Models (`src/regime/`)**
    - [ ] Implement Hidden Markov Model (HMM) classifier.
    - [ ] Implement K-means clustering classifier.
    - [ ] Implement Bayesian Online Change-Point Detection (BOCPD).
- [ ] **Regime-Conditional Execution**
    - [ ] Connect regime output and confidence scores to dynamic buy/sell sizing multipliers.
    - [ ] Implement hysteresis filtering (wait 3 consecutive 4h candles or confidence score $> 0.95$).
    - [ ] *Testing:* Walk-forward cross validation checks with Combinatorial Purged Cross Validation (CPCV).

### Phase 4 — Reinforcement Learning Optimization
- [ ] **Market Simulator (`src/simulator/`)**
    - [ ] Build synthetic market simulator (GBM with regime-switching volatility).
    - [ ] Implement GAN / diffusion-based generator trained on historical features.
    - [ ] Validate simulator using stylized-fact tests.
- [ ] **RL Agent Training (`src/ai/`)**
    - [ ] Build custom Gym environment exposing state vector and action space.
    - [ ] Design the reward function incorporating `btc_growth`, drawdown penalty, overtrading penalty, and `hodl_underperformance_penalty`.
    - [ ] Implement Offline RL (CQL/IQL) warm-start pipelines.
    - [ ] Train RL agent using Stable-Baselines3/CleanRL.
    - [ ] Evaluate Probability of Backtest Overfitting (PBO).
    - [ ] *Testing:* Assert target $PBO < 0.5$ on final model checkpoint.

### Phase 5 — Paper Trading
- [ ] **Live Execution Setup (`src/execution/`)**
    - [ ] Implement real CCXT Binance API client integration (Trade-only API key verification).
    - [ ] Set up live WebSocket handlers for tickers, orderbooks, and user data streams.
- [ ] **Paper Trading Pipeline**
    - [ ] Deploy system to run with live data and simulated order execution.
    - [ ] Build Prometheus & Grafana dashboard to track performance in real-time.
    - [ ] Implement Telegram warning exporter.
- [ ] **Reconciliation & Validation**
    - [ ] Monitor and log execution latency, slippage, and fill quality.
    - [ ] *Testing:* Conduct chaos tests (disconnect internet, mock rate limits, inject wrong WS payloads) and assert system recovers or halts correctly.
    - [ ] Verify that zero invariant violations and zero kill-switch misfires occur over a 3-month trial.

### Phase 6 — Small Capital Deployment
- [ ] **Small-Scale Live Run**
    - [ ] Fund account with $\le 1\%$ of planned target capital.
    - [ ] Run live execution with real funds on Binance.
    - [ ] Conduct daily ledger audits reconciling DB state with exchange state.
    - [ ] Complete a 3-month live evaluation period before scaling up.
    - [ ] *Testing:* Confirm zero discrepancies on daily audit reports.

### Phase 7 — Delta-Neutral Sleeve (Optional)
- [ ] **Delta-Neutral Engine (`src/execution/`)**
    - [ ] Build the funding-harvesting module (opening spot-long vs. perp-short).
    - [ ] Code risk managers monitoring basis risk and perp liquidation boundaries.
    - [ ] Implement isolated ledger tracking for delta-neutral trades.
    - [ ] *Testing:* Unit test basis calculation and liquidation buffers.
