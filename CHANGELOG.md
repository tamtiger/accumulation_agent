# Changelog

All notable changes to the Adaptive BTC Accumulation System (ABAS) — v2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.9] - 2026-06-12

### Fixed & Aligned
- **Specification Alignments**:
  - Corrected **Bear Market Multipliers** in `GridEngine` to use spec-compliant `1.1` for buy (was `0.4`) and `0.4` for sell (was `0.8`).
  - Adjusted **Panic Dump Buy Multiplier** to `1.75` (spec range `1.5-2.0`).
  - Added **Funding Rate Kill Switch** checking `funding_rate > 0.3%/8h` to pause aggressive buys.
  - Implemented **30-Minute Auto-Recovery** for soft risk triggers (API error rate, spread, stablecoin peg, reserve floor, funding rate).
  - Implemented **Double Trigger Halt Circuit Breaker** requiring manual resume if a kill switch fires twice in 24 hours.
  - Fixed **48-Hour Local Low Expiration** resetting `anchored_local_low` after 48h of inactivity.
  - Fixed **5/7 Days Custody Sweep** to be conditional on recent sell orders in `trade_history` (otherwise requiring 7/7 consecutive days).
  - Configured `delta_neutral_enabled` defaults in `config/production.json`.
- **Codebase Bugs**:
  - Standardized **Database Connection Pool Management** across `ABASOrchestrator` and `CustodySweeper` to prevent connection leaks.
  - Resolved **GaussianHMM Global RNG side-effects** by replacing global seed with local `numpy.random.default_rng`.
  - Resolved **BOCPD Memory Leak** by truncating run-length distribution arrays to a maximum size of `500` elements and re-normalizing `R`.
  - Fixed **Online Feature Querying** in `FeatureEngine` by joining TimescaleDB tables for funding rate and open interest, and subquerying liquidations.
  - Corrected **CustodySweeper Parameter Gating** to assign `trading_target` and `promotion_threshold_multiplier` correctly in constructor.
  - Fixed undefined name `Optional` in `RiskOverlay` and resolved all unused imports/variables across the codebase (verified with clean `ruff check`).
  - Added missing `aiohttp` dependency in `pyproject.toml`.

## [2.1.8] - 2026-06-11

### Added
- **Core Constraints & Compounding**:
  - Implemented **Accumulation Guard** capping the buy multiplier deep underwater to prevent blowing through reserves too early in a cycle.
  - Implemented **180-day Gating Exception** in GridEngine to force sell lots held longer than 180 days even if underwater (for tax loss harvesting purposes).
  - Implemented **30/70 PnL Split**: On profitable sells, 30% of the net profit is extracted to fiat/USDT reserve, and 70% is compounded into the core BTC stash.
- **Resilience & Execution**:
  - Implemented `BinanceMock` fallback logic in both the `ABASOrchestrator` main loop and the `reconcile_audit` script to gracefully permit local execution (Paper Trading without Binance API Keys).

### Fixed
- Fixed `RuntimeWarning: divide by zero encountered in log` in HMM regime predictor by clipping probabilities before log calculations.
- Suppressed legacy DBAPI2 SQLAlchemy warnings emitted by `pandas`.
- Fixed missing columns error (`column "funding_rate" does not exist`) by removing cross-table references from the primary `binance_ohlcv` query in `FeatureEngine`.
- Fixed Orchestrator and Audit script execution by enforcing module mode execution (`-m src...`) and updating documentation across `README.md`.
- Added missing main execution block and tracebacks to `src/portfolio/reconcile_audit.py` for manual daily auditing.

## [2.1.7] - 2026-06-11

### Added
- **Phase 7: Delta-Neutral Sleeve (Optional)**:
  - Implemented `DeltaNeutralManager` in `src/execution/delta_neutral.py` to harvest perpetual funding rates.
  - Implemented isolated ledger logging, basis spread divergence checks, and perp liquidation risk managers.
  - Integrated the Delta-Neutral sleeve in `ABASOrchestrator` (`src/execution/orchestrator.py`) with configuration controls.
  - Added spot balance isolation in orchestrator syncing to prevent Delta-Neutral spot positions from interfering with the core grid sleeve.
  - Enhanced `BinanceMock` to support simulated perpetual orders, fees, and short position PnL.
  - Added unit test suite in `tests/test_delta_neutral.py` validating engine logic and orchestrator integration.

## [2.1.6] - 2026-06-11

### Added
- **Phase 6: Small Capital Deployment**:
  - Aligned CCXT `create_order` parameters in `ABASOrchestrator` to match the official CCXT signature (`type="limit"`).
  - Back-ported standard `type` parameter mapping to `BinanceMock` and `BinancePaper` execution wrappers.
  - Implemented `LedgerAuditor` in `src/portfolio/reconcile_audit.py` to reconcile live exchange balances against database states and write daily audit reports.
  - Added automated Telegram discrepancy alerts when database values diverge from actual exchange balances.

## [2.1.5] - 2026-06-11

### Added
- **Phase 5: Paper Trading**:
  - Implemented real-time market data streaming via `BinanceWSClient` using `aiohttp` websockets.
  - Implemented `BinancePaper` execution client which queries live balances, simulates fills and slippage versus orderbook depth, and enforces read-only safety checks.
  - Enabled API key permissions auditing to automatically assert withdrawal features are disabled at startup.
  - Integrated paper trading in the orchestrator pipeline.

## [2.1.4] - 2026-06-11

### Added
- **Phase 4: Reinforcement Learning Optimization**:
  - Created `GBMSimulator` and `MSARGenerator` in pure NumPy for generating synthetic returns with volatility clustering and fat tails.
  - Implemented `StylizedFactsValidator` to check for kurtosis and autocorrelation of absolute returns.
  - Implemented custom `ABASGymEnv` environment mapping trading states, executing spacing/deployment actions, and calculating rewards.
  - Implemented `NumPyRLAgent` mapping states to actions using a Gaussian Policy Gradient (REINFORCE) network.
  - Implemented `PBOEvaluator` calculating Probability of Backtest Overfitting.

## [2.1.3] - 2026-06-11

### Added
- **Phase 3: AI Overlay (Regime Detection)**:
  - Implemented `GaussianHMM` in pure NumPy with Baum-Welch training and Viterbi sequence decoding.
  - Implemented `NumPyKMeans` clustering for multi-feature classification.
  - Implemented `BOCPD` (Bayesian Online Change-Point Detection) with Normal-Gamma prior.
  - Developed `RegimeClassifier` supporting centroid-based post-hoc semantic mapping, confidence calculation, and 3-tick hysteresis filtering.
  - Integrated regime detection with the orchestrator (`src/execution/orchestrator.py`) for dynamic sizing and spacing adjustments.
  - Updated build commands and tests to run via `uv` toolchain.

## [2.1.2] - 2026-06-10

### Fixed & Optimized
- **Phase 2: Historical Backtesting & Validation**:
  - Solved `DataGapError` infinite loop by updating `last_timestamp` before raising the exception in `DataValidator`.
  - Resolved low-volatility outliers quarantine by adding minimum standard deviation floors (1% for price, 10% for volume) in z-score calculations.
  - Initialized mock exchange's trading BTC balance to `0.0` in the backtest harness to avoid immediate INV-7 halts.
  - Adapted daily deployment cap check, custody sweep, ledger updates, and portfolio snapshots to use tick/simulation time instead of database `NOW()`.
  - Aligned risk overlay with safety specs so reserve ratio below floor pauses buys only (via a `buys_paused` flag) rather than triggering system halts.
  - Improved orchestrator error handling to prevent soft `InvariantViolationError` rejections from marking the system as permanently halted.
  - Successfully executed full backtesting simulations and parameter sweeps, generating the performance report at [backtest_report.md](artifacts/backtest_report.md).

## [2.1.1] - 2026-06-10

### Added
- **Harness Integration**:
  - Initialized Harness-OS configurations under `.harness/` (including `verify.yaml`, `config.yaml`, `feature_list.json`, `repo-summary.md`, and `scope.yaml`).
  - Added [AGENTS_HARNESS.md](AGENTS_HARNESS.md) outlining testing, verification, and lifecycle instructions.

### Changed & Fixed
- **System Specification Update (v2.1)**:
  - Updated [ABAS_PLAN_v2.md](ABAS_PLAN_v2.md) and [ABAS_PLAN_v2_VI.md](ABAS_PLAN_v2_VI.md) to address core logic flaws from the plan review (including the Buy/Sell basis asymmetry, FIFO head lock mitigation with the 180-day exception, corrected bear market multipliers, and definition of `A_local_low` reset conditions).
- **Code Cleanups & Refactoring**:
  - Removed unused imports (such as `os` and `logging`) and standardized formatting across codebase files (including [src/config.py](src/config.py), [src/risk/overlay.py](src/risk/overlay.py), [src/custody/sweeper.py](src/custody/sweeper.py), and related tests).
  - Normalized line endings to CRLF for Windows compatibility.

## [2.1.0] - 2026-05-25

### Added
- **Tax Matching & Export**:
  - Implemented `tax_records` database table schema and `save_tax_record`/`get_tax_records` repository methods to store matching FIFO lot consumptions on sells.
  - Implemented CSV export functionality `export_tax_report_csv` in `FIFOLedger` matching tax tool formats (Koinly, CoinTracker).
- **Core Parameters**:
  - Added the missing `inv3_epsilon` config parameters in Pydantic Settings class and `config/production.json` default settings.
- **Verification Tests**:
  - Added unit test `test_risk_overlay_inv5_sell_gating_fifo_head` checking that `INV-5` enforces profit margins strictly against the FIFO head lot purchase price.
  - Added unit test `test_risk_overlay_inv3_limit_order_different_price` verifying that limit orders proposed at a price different from the spot price pass value conservation audits without false halts.

### Changed & Fixed
- **INV-5 Sell Gating**:
  - Updated `GridEngine.calculate_sell_size` and `RiskOverlay` to evaluate the sell gate margin check against `avg_cost_fifo_lot` instead of the global portfolio average cost basis (`avg_cost`).
- **INV-3 Value Conservation**:
  - Rewrote the conservation check in `RiskOverlay.check_invariants` to compare proposed states against expected order execution values within `inv3_epsilon` (for BTC), allowing limit orders to be placed without triggering false value-leak halts.
- **Custody Sweeper Snapshot**:
  - Updated the DB query in `src/custody/sweeper.py` to aggregate tick-by-tick state history into daily snapshots (`DISTINCT ON (date_trunc('day', time))`), evaluating the 7 consecutive days rule using daily balances instead of individual tick balances.
- **Live Slippage Audit**:
  - Modified live slippage tracking in the orchestrator to calculate slippage dynamically versus the tick mark price at placement, resolving the live CCXT bypass where CCXT does not return custom `"slippage"` response keys.
- **Dynamic A_local_low**:
  - Replaced hardcoded `local_low = a_mean * 0.97` with dynamic calculations of `A_local_low_48h` (rolling 48h minimum low) in `FeatureEngine` batch and online paths, which is anchored at rebound detection and reset after a sell fills.

## [2.0.0] - 2026-05-23

### Added
- **Test Infrastructure & Optimization Fixes**
  - Created global test configuration [tests/conftest.py](tests/conftest.py) mock-patching Redis and PostgreSQL connection pools to execute tests instantly without network dependencies.
  - Added mock coverage for `InventoryRepository.get_active_lots` in [tests/test_backtest.py](tests/test_backtest.py) and [tests/test_orchestrator.py](tests/test_orchestrator.py) to prevent connection pool attempts.
  - Fixed assertion formulas in [tests/test_portfolio.py](tests/test_portfolio.py) (exposure tracking calculation) and adjusted `hot_exchange_cap` bounds in [tests/test_orchestrator.py](tests/test_orchestrator.py) to avoid false-positive invariant violations.
  - Resolved urllib context manager mocking issues in [tests/test_monitoring.py](tests/test_monitoring.py) and connection releasing in [tests/test_custody.py](tests/test_custody.py).

- **Phase 1: Rule-Based Prototype Engine**
  - **Data Ingestion**: Implemented validation schemas and gap/outlier detection in [src/data/validators.py](src/data/validators.py), and Binance ticker ingester in [src/data/ingester.py](src/data/ingester.py) publishing to Redis.
  - **Feature Engine**: Added technical indicators and anchor calculations ($A_{\text{trend}}$, $A_{\text{range}}$, $A_{\text{vol}}$, $A_{\text{mean}}$, and annualized volatility $\sigma_{\text{ann}}$) in [src/features/engine.py](src/features/engine.py).
  - **Inventory Engine**: Implemented per-lot FIFO queue tracking, cost-basis calculations, and P&L ledger tracking in [src/inventory/ledger.py](src/inventory/ledger.py) and TimescaleDB repository queries in [src/inventory/models.py](src/inventory/models.py).
  - **Adaptive Grid**: Created grid spacing rules scaled by volatility and drawdown buy multipliers in [src/grid/engine.py](src/grid/engine.py).
  - **Risk Overlay**: Implemented strict invariant audits (`INV-1` to `INV-7`) and automated kill switch monitoring in [src/risk/overlay.py](src/risk/overlay.py).
  - **Execution & Orchestrator**: Created CCXT mock execution simulator in [src/execution/ccxt_mock.py](src/execution/ccxt_mock.py) and sequential tick coordinator with Redis heartbeats in [src/execution/orchestrator.py](src/execution/orchestrator.py).
  - **Portfolio Tracking**: Added DB-to-exchange reconciliation checks in [src/portfolio/tracker.py](src/portfolio/tracker.py).
  - **Custody Sweeper**: Implemented 7-day target breach detection and strategic sweeps in [src/custody/sweeper.py](src/custody/sweeper.py).
  - **Monitoring**: Created Prometheus exporter metrics and Telegram alert dispatchers in [src/monitoring/exporter.py](src/monitoring/exporter.py).
  - **Backtest Harness**: Implemented historical tick-by-tick simulation replay with tax liability calculations in [src/backtest/harness.py](src/backtest/harness.py).
  - **Test Suite**: Developed 29 unit, integration, and property-based test cases under `tests/`.

- **Phase 0: Project Infrastructure**
  - Scaffolded repository structure (`src/`, `tests/`, `config/`).
  - Added [pyproject.toml](pyproject.toml) declaring core dependencies (`ccxt`, `numpy`, `pandas`, `pydantic-settings`, `psycopg2-binary`, `redis`, `prometheus-client`) and dev/test requirements.
  - Configured [docker-compose.yml](docker-compose.yml) exposing TimescaleDB (PostgreSQL 15) and Redis services compatible with Podman.
  - Implemented [config/production.json](config/production.json) containing core parameters (`reserve_floor`, `daily_deployment_cap`, `hot_exchange_cap`, `min_profit_threshold`, etc.).
  - Added [src/config.py](src/config.py) validating settings via Pydantic Settings and loading environmental variable overrides.
  - Implemented [src/utils/logging.py](src/utils/logging.py) providing structured JSON logs and automatic redaction of sensitive credentials.
  - Implemented database auto-initialization [src/utils/init_db.py](src/utils/init_db.py) creating TimescaleDB hypertables.
  - Added CI workflow configuration in `.github/workflows/ci.yml`.

### Changed
- Updated author metadata name (`tamtiger`) and email (`tam.supersoft@gmail.com`) in `pyproject.toml`.
