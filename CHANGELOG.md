# Changelog

All notable changes to the Adaptive BTC Accumulation System (ABAS) — v2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
  - Created global test configuration [tests/conftest.py](file:///d:/MyProject/accumulation_agent/tests/conftest.py) mock-patching Redis and PostgreSQL connection pools to execute tests instantly without network dependencies.
  - Added mock coverage for `InventoryRepository.get_active_lots` in [tests/test_backtest.py](file:///d:/MyProject/accumulation_agent/tests/test_backtest.py) and [tests/test_orchestrator.py](file:///d:/MyProject/accumulation_agent/tests/test_orchestrator.py) to prevent connection pool attempts.
  - Fixed assertion formulas in [tests/test_portfolio.py](file:///d:/MyProject/accumulation_agent/tests/test_portfolio.py) (exposure tracking calculation) and adjusted `hot_exchange_cap` bounds in [tests/test_orchestrator.py](file:///d:/MyProject/accumulation_agent/tests/test_orchestrator.py) to avoid false-positive invariant violations.
  - Resolved urllib context manager mocking issues in [tests/test_monitoring.py](file:///d:/MyProject/accumulation_agent/tests/test_monitoring.py) and connection releasing in [tests/test_custody.py](file:///d:/MyProject/accumulation_agent/tests/test_custody.py).

- **Phase 1: Rule-Based Prototype Engine**
  - **Data Ingestion**: Implemented validation schemas and gap/outlier detection in [src/data/validators.py](file:///d:/MyProject/accumulation_agent/src/data/validators.py), and Binance ticker ingester in [src/data/ingester.py](file:///d:/MyProject/accumulation_agent/src/data/ingester.py) publishing to Redis.
  - **Feature Engine**: Added technical indicators and anchor calculations ($A_{\text{trend}}$, $A_{\text{range}}$, $A_{\text{vol}}$, $A_{\text{mean}}$, and annualized volatility $\sigma_{\text{ann}}$) in [src/features/engine.py](file:///d:/MyProject/accumulation_agent/src/features/engine.py).
  - **Inventory Engine**: Implemented per-lot FIFO queue tracking, cost-basis calculations, and P&L ledger tracking in [src/inventory/ledger.py](file:///d:/MyProject/accumulation_agent/src/inventory/ledger.py) and TimescaleDB repository queries in [src/inventory/models.py](file:///d:/MyProject/accumulation_agent/src/inventory/models.py).
  - **Adaptive Grid**: Created grid spacing rules scaled by volatility and drawdown buy multipliers in [src/grid/engine.py](file:///d:/MyProject/accumulation_agent/src/grid/engine.py).
  - **Risk Overlay**: Implemented strict invariant audits (`INV-1` to `INV-7`) and automated kill switch monitoring in [src/risk/overlay.py](file:///d:/MyProject/accumulation_agent/src/risk/overlay.py).
  - **Execution & Orchestrator**: Created CCXT mock execution simulator in [src/execution/ccxt_mock.py](file:///d:/MyProject/accumulation_agent/src/execution/ccxt_mock.py) and sequential tick coordinator with Redis heartbeats in [src/execution/orchestrator.py](file:///d:/MyProject/accumulation_agent/src/execution/orchestrator.py).
  - **Portfolio Tracking**: Added DB-to-exchange reconciliation checks in [src/portfolio/tracker.py](file:///d:/MyProject/accumulation_agent/src/portfolio/tracker.py).
  - **Custody Sweeper**: Implemented 7-day target breach detection and strategic sweeps in [src/custody/sweeper.py](file:///d:/MyProject/accumulation_agent/src/custody/sweeper.py).
  - **Monitoring**: Created Prometheus exporter metrics and Telegram alert dispatchers in [src/monitoring/exporter.py](file:///d:/MyProject/accumulation_agent/src/monitoring/exporter.py).
  - **Backtest Harness**: Implemented historical tick-by-tick simulation replay with tax liability calculations in [src/backtest/harness.py](file:///d:/MyProject/accumulation_agent/src/backtest/harness.py).
  - **Test Suite**: Developed 29 unit, integration, and property-based test cases under `tests/`.

- **Phase 0: Project Infrastructure**
  - Scaffolded repository structure (`src/`, `tests/`, `config/`).
  - Added [pyproject.toml](file:///d:/MyProject/accumulation_agent/pyproject.toml) declaring core dependencies (`ccxt`, `numpy`, `pandas`, `pydantic-settings`, `psycopg2-binary`, `redis`, `prometheus-client`) and dev/test requirements.
  - Configured [docker-compose.yml](file:///d:/MyProject/accumulation_agent/docker-compose.yml) exposing TimescaleDB (PostgreSQL 15) and Redis services compatible with Podman.
  - Implemented [config/production.json](file:///d:/MyProject/accumulation_agent/config/production.json) containing core parameters (`reserve_floor`, `daily_deployment_cap`, `hot_exchange_cap`, `min_profit_threshold`, etc.).
  - Added [src/config.py](file:///d:/MyProject/accumulation_agent/src/config.py) validating settings via Pydantic Settings and loading environmental variable overrides.
  - Implemented [src/utils/logging.py](file:///d:/MyProject/accumulation_agent/src/utils/logging.py) providing structured JSON logs and automatic redaction of sensitive credentials.
  - Implemented database auto-initialization [src/utils/init_db.py](file:///d:/MyProject/accumulation_agent/src/utils/init_db.py) creating TimescaleDB hypertables.
  - Added CI workflow configuration in `.github/workflows/ci.yml`.

### Changed
- Updated author metadata name (`tamtiger`) and email (`tam.supersoft@gmail.com`) in `pyproject.toml`.
