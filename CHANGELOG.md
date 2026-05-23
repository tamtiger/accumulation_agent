# Changelog

All notable changes to the Adaptive BTC Accumulation System (ABAS) — v2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
