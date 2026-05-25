# AGENTS_REPO.md — Repository Context & Architecture Notes

> Load this file when reading, writing, or navigating the codebase.

---

## 1. Repository Layout

```
accumulation_agent/
├── config/
│   ├── production.json       # Live runtime parameters (no secrets here)
│   ├── paper.json            # Paper trading overrides
│   └── test.json             # Test environment overrides
├── src/
│   ├── data/                 # Data ingestion, validation, gap detection
│   ├── features/             # ATR, EMA, RSI, funding rate, OI, σ_ann
│   ├── regime/               # HMM, K-means, BOCPD change-point detection
│   ├── inventory/            # FIFO ledger, cost basis, bucket state machine
│   ├── grid/                 # Adaptive grid engine, order sizing
│   ├── risk/                 # Invariant enforcement, kill switches, halt logic
│   ├── execution/            # CCXT wrappers, order routing, orchestrator
│   ├── portfolio/            # Balance tracking, daily reconciliation
│   ├── backtest/             # vectorbt / backtrader harness
│   ├── simulator/            # Synthetic market generator (Phase 4+)
│   ├── ai/                   # RL agents (Stable-Baselines3 / CleanRL)
│   ├── custody/              # Cold sweep logic, core promotion signals
│   ├── monitoring/           # Prometheus exporters, Telegram/SMS alerts
│   └── api/                  # Internal service API
├── tests/
│   ├── unit/                 # Per-module unit tests
│   ├── property/             # Hypothesis property-based tests
│   ├── replay/               # Deterministic backtest snapshots
│   └── chaos/                # Fault injection tests
├── scripts/                  # One-off ops scripts (migrations, audits)
├── docker-compose.yml
├── requirements.txt
├── ABAS_PLAN_v2.md
├── AGENTS.md
├── AGENTS_SAFETY.md
├── AGENTS_SPECS.md
├── AGENTS_CONFIG.md
├── AGENTS_REPO.md
├── AGENTS_CONVENTIONS.md
└── README.md                 # Quick-start (Vietnamese)
```

---

## 2. Key Files

| File | Why it matters |
|---|---|
| `src/inventory/fifo_ledger.py` | Core FIFO logic — changes here affect INV-5 directly |
| `src/risk/invariants.py` | Hard-coded invariant checks — the final safety gate |
| `src/execution/orchestrator.py` | Tick loop, agent coordination, bootstrapping phases |
| `src/regime/classifier.py` | HMM + K-means model, hysteresis filter |
| `config/production.json` | All tunable parameters |
| `tests/property/test_invariants.py` | INV-1, INV-3, sell gating property tests |

---

## 3. External Services

| Service | Role | Notes |
|---|---|---|
| Binance Spot | Primary exchange | REST + WebSocket via CCXT Pro |
| PostgreSQL + TimescaleDB | Primary DB | Candles, ledger, snapshots — all hypertables |
| Redis | Pub/Sub + heartbeat | Agent message bus, `heartbeat:<agent_name>` keys |
| Prometheus + Grafana | Metrics & dashboards | All agents export via Prometheus client |
| Telegram API | Alerts | HALT events, daily summaries |
| HashiCorp Vault / Cloud KMS | Secrets | API keys, DB creds — never in code or config files |

---

## 4. Database Schema (key tables)

All tables are TimescaleDB hypertables, partitioned by `timestamp`.

| Table | Schema |
|---|---|
| `fifo_lots` | `lot_id, qty, purchase_price, timestamp, regime_tag, status, realized_pnl_usd` |
| `order_fills` | `fill_id, order_id, side, qty, price, mid_price_at_placement, slippage, timestamp, tick_id` |
| `portfolio_snapshots` | `tick_id, timestamp, core_btc, trading_btc, reserve_usdt, total_value_btc` |
| `regime_history` | `tick_id, timestamp, regime_label, confidence, hmm_state` |
| `invariant_checks` | `tick_id, timestamp, inv_id, passed, detail` |
| `halt_events` | `event_id, timestamp, trigger, detail, resolved_at` |

---

## 5. Data Flow (per tick)

```
Binance WS / CCXT REST
        │
        ▼
[Data Agent] ─── gap / outlier detection ──► halt if bad
        │
        ▼  clean OHLCV + funding + OI + liquidations
[Feature Agent] ─── computes anchors + σ_ann + state vector
        │
        ▼  feature vector
[Regime Agent] ─── HMM + K-means + BOCPD ──► regime + confidence C
        │                                     (fallback: Sideways if C < 0.40)
        ▼
[Inventory Agent] ─── reads FIFO ledger ──► avg_cost_fifo_lot, trading_btc_qty, reserve_usdt
        │
        ▼
[Grid Agent] ─── proposes buy/sell grid ──► unsigned order list
        │          (σ_ann, regime multipliers, A_range, A_local_low, INV-5 pre-check)
        ▼
[Risk Agent] ─── validates INV-1 to INV-7 + kill switches ──► approved order list
        │
        ▼
[Execution Agent] ─── submits to Binance via CCXT ──► fill reports + slippage log
        │
        ▼
[Portfolio Agent] ─── reconciles exchange vs DB ──► discrepancy alert if > 0.01%
        │
        ▼
[Inventory Agent] ─── updates FIFO ledger with fills ──► new cost basis
        │
        ▼
[Monitoring Agent] ─── Prometheus export, heartbeat audit, HALT broadcast if needed
```

---

## 6. Design Principles

1. **Rule-based core, AI as overlay.** Buy/sell thresholds, invariants, and kill switches are explicit and deterministic. AI adjusts sizing parameters within bounded ranges only — it never overrides safety rules.

2. **Single source of truth for state.** Only the Inventory Agent writes portfolio state. All others read and propose mutations via the Orchestrator.

3. **Strict tick serialization.** No parallel execution within a tick. Every decision sees a consistent state snapshot.

4. **Fail loud, fail fast.** Missing data, invariant violations, unexpected fills → explicit halt. Silent failures are a risk to capital.

5. **BTC-native accounting.** All metrics, drawdowns, and optimization targets are in BTC quantity. USDT is ammunition, not the scoreboard.

---

## 7. Known Limitations & Deferred Work

| Limitation | Status | Resolution |
|---|---|---|
| Single exchange (Binance only) | Active | Multi-exchange routing in Phase 5+ |
| No live config reload | Active | Accepted — hot-reload would break tick consistency |
| Single tax jurisdiction | Active | Multi-jurisdiction support post-Phase 2 |
| RL simulator not built | Deferred | Required before Phase 4 |
| Delta-neutral sleeve off | Deferred | Phase 7, after Phase 6 stable |
| No automated cold wallet sweep | Active | Promotion signal triggers manual sweep; auto-sweep in custody module later |
