# Adaptive BTC Accumulation System (ABAS) — v2

> Long-term BTC accumulation engine using volatility harvesting, adaptive inventory management, and AI-assisted regime detection.
>
> **Version:** 2.1 (patched)
> **Primary objective:** Maximize BTC holdings over multiple market cycles, net of fees and taxes, vs. passive HODL benchmark.

---

## Changelog v2.0 → v2.1 (patch)

| Area | Change |
|---|---|
| Bootstrapping | **[FIX]** Unified B1/B2/B3 percentages — was inconsistent between plan and AGENTS.md |
| INV-3 | **[FIX]** Changed from strict equality to epsilon tolerance to handle floating-point and unsettled fees |
| INV-5 sell gating | **[FIX]** Clarified that sell gate checks the FIFO lot price to be consumed, not the global avg_cost |
| Local low definition | **[FIX]** Defined "local low" as rolling min(low, 48h) anchored at the point of rebound detection |
| trading_floor unit | **[FIX]** Clarified trading_floor is expressed as % of total_portfolio value |
| Kill switch drawdown | **[FIX]** Defined drawdown reference point as portfolio value at 00:00 UTC of the rolling window start |
| Tax reporting | **[ADD]** Added explicit tax accounting and FIFO export requirements |
| Slippage definition | **[FIX]** Corrected slippage formula — measured vs mid-price at order placement, not vs limit price |

## Changelog v1 → v2

| Area | Change |
|---|---|
| Buy/Sell anchors | Added rolling anchor + cost-basis logic |
| Bootstrapping | New section defining initial portfolio construction |
| Core BTC | Added promotion rules from trading bucket |
| Benchmarks | Passive HODL in BTC terms is now primary benchmark |
| Fees & tax | Explicit modeling, sensitivity analysis required |
| Regime conflict | Regime-conditional sizing multiplier |
| Custody | Split policy: core cold, trading hot, reserve diversified |
| RL data budget | Added synthetic market simulator requirement |
| Regime labeling | Unsupervised (HMM/clustering) only |
| Cost basis | Per-lot tracking added to state |
| Sell gating | Minimum profit threshold required |
| Funding harvest | New delta-neutral sleeve (optional) |
| Kill switch | New section |
| Security | New section |
| Invariants | New section |
| Failure playbook | New section |

---

# 1. Core Philosophy

## Objective

The system DOES NOT optimize:

```
Max USDT profit
```

The system optimizes:

```
Max BTC holdings over time, net of fees and taxes,
vs. passive HODL in BTC terms.
```

BTC is treated as:
- Primary reserve asset
- Long-term store of value
- Strategic inventory

USDT is treated as:
- Ammunition
- Liquidity reserve
- Rebalancing tool

---

# 2. Strategic Concept

```
Buy fear
Sell partial rebounds
Rebuy deeper discounts
Accumulate BTC through volatility
```

Similar to:
- Volatility harvesting
- Dynamic DCA
- Inventory trading
- Long-biased market making

Constraints:
- Always maintain long BTC exposure
- Never sell below cost basis (sell-gating rule)
- Never deplete reserve below floor

---

# 3. Assumptions & Invariants

## Assumptions (must hold for system to work)

| Assumption | Mitigation if violated |
|---|---|
| BTC has positive long-term drift | System still accumulates in sideways; fails in prolonged bear with no recovery |
| Volatility is mean-reverting at some horizon | Adaptive grid auto-widens |
| Exchange availability ≥ 99% | Multi-exchange routing (Phase 5+) |
| Stablecoin peg holds ≥ 99% time | Diversified reserve (USDT/USDC/short T-bills) |
| No systemic regulatory shutdown | Self-custody core; exchange holds only trading bucket |

## Invariants (must ALWAYS be true — enforced in code)

```
INV-1: core_btc_qty is monotonically non-decreasing
INV-2: reserve_usdt >= reserve_floor (% of portfolio)
INV-3: abs(sum(buckets) - total_portfolio) < EPSILON   # EPSILON = 1e-8 BTC
        # Strict equality is infeasible due to floating-point arithmetic,
        # partial fills in-flight, and unsettled fee accruals.
INV-4: no order placed if it would violate INV-1 or INV-2
INV-5: no sell order placed if the FIFO lot price to be consumed < avg_cost_fifo_lot * (1 + min_profit_threshold)
        # Note: uses cost of the specific lot being sold (FIFO head), NOT global avg_cost.
        # This prevents selling a high-cost early lot at a loss even when global avg_cost is lower.
INV-6: daily_deployed_capital <= daily_deployment_cap
INV-7: total BTC on hot exchange <= hot_exchange_cap
```

These are **hard asserts** — violation halts the system.

---

# 4. System Objectives

| Objective | Description |
|---|---|
| Accumulate BTC | Increase BTC quantity over time (vs HODL baseline) |
| Survive volatility | Avoid reserve depletion in extended drawdowns |
| Harvest market noise | Profit from swings in BTC terms |
| Avoid overtrading | Minimize unnecessary churn and fee/tax drag |
| Preserve core exposure | Never lose BTC positioning |
| Survive counterparty failure | Limit exchange exposure |

---

# 5. High-Level Architecture

```
Market Data Layer
        ↓
Data Validation & Cleaning
        ↓
Feature Engine
        ↓
Regime Detection Layer (HMM / unsupervised)
        ↓
Inventory Management Engine  ← Cost Basis Tracker (FIFO per-lot)
        ↓
Adaptive Grid Engine
        ↓
Risk Overlay  ← Kill Switch / Circuit Breakers
        ↓
Execution Engine
        ↓
Portfolio Tracking (core / trading / reserve)
        ↓
Monitoring & Analytics
```

---

# 6. Portfolio Structure

## Capital Allocation (target steady-state)

| Bucket | Allocation | Purpose | Custody |
|---|---|---|---|
| Core BTC | 60–80% | Never sell | Cold storage |
| Trading BTC | 10–25% | Swing inventory | Hot exchange |
| USDT Reserve | 10–20% | Buy crashes | Diversified stables / T-bills |

## Reserve Diversification (within USDT Reserve bucket)

| Sub-asset | Share | Notes |
|---|---|---|
| USDT | 40–50% | Deepest liquidity on Binance |
| USDC | 30–40% | Depeg-decorrelated with USDT |
| DAI / short T-bill tokens | 10–20% | Off-exchange yield option |

## Custody Policy

- Core BTC: **cold wallet**, multisig or hardware
- Sweep rule: when hot-exchange BTC > `hot_exchange_cap` (e.g., 25% of total BTC), auto-transfer excess to cold
- API keys: trade-only, withdrawal disabled, IP-whitelisted

---

# 7. Bootstrapping (Day 0 → Steady State)

**Problem:** On day 1, how do we build the 60–80% core without either lump-summing the top or missing the ride?

**Strategy:** 3-phase ramp.

> **[v2.1 FIX]** Percentages below are the authoritative values. AGENTS.md Section 2.10 must match these exactly. Any discrepancy defaults to this document.

| Phase | Duration | Action |
|---|---|---|
| Phase B1 — Seed | Week 1 | Deploy **20% of total planned capital** immediately (market buy, split across core + trading seed) |
| Phase B2 — DCA ramp | Weeks 2–12 | Deploy **60% of remaining capital** via weekly DCA schedule (~6% per week of remaining) |
| Phase B3 — Opportunistic | Weeks 4–26 | Reserve **20% of total planned capital** for dips >1σ below 90-day mean; deploy adaptively |

Trading bucket and reserve are built in parallel as core fills.

**Rationale:** Removes discretion, limits regret, captures both trend continuation and mean reversion.

---

# 8. Inventory Management Engine

## Philosophy

The agent thinks:

```
How do I increase BTC inventory per unit of risk?
```

NOT:

```
Can I predict the next candle?
```

## Cost Basis Tracker (required component)

- Per-lot FIFO ledger of every BTC buy: `(lot_id, qty, purchase_price, timestamp, regime_tag)`
- Computes:
  - `avg_cost_fifo_lot`: cost of the specific lot at FIFO head (used in INV-5 sell gating)
  - `avg_cost_portfolio`: weighted average across all remaining lots (used in state/reporting)
  - `realized_pnl_btc`, `unrealized_pnl_btc`
- Persisted to DB; reconciled against exchange fills daily
- Export-ready for tax reporting (see Section 19)

---

# 9. Reference Anchors (Critical)

All buy/sell thresholds are defined relative to explicit anchors, not "price drops X%".

| Anchor | Definition | Used for |
|---|---|---|
| `A_trend` | EMA(200, daily) | Macro trend filter |
| `A_range` | Rolling max(high, 30d) | Drawdown-from-peak trigger |
| `A_vol` | ATR(14) / price | Adaptive grid spacing (proxy only; use σ_ann for grid sizing) |
| `A_cost` | Per-lot FIFO cost basis | Sell gating (INV-5) |
| `A_mean` | EMA(20, 4h) | Mean-reversion anchor |
| `A_local_low` | Rolling min(low, 48h) | Rebound trigger reference — see Section 10 |

A "drop of X%" is always `(A_anchor − price) / A_anchor` with the anchor specified in the rule.

---

# 10. Core Trading Logic

## Buy Logic (regime-conditional)

Base deployment table (percent of **remaining reserve**, not total portfolio):

| Drawdown from `A_range` | Base reserve deploy |
|---|---|
| −3% | 5% |
| −6% | 10% |
| −10% | 20% |
| −15% | 30% |
| −25% | 40% |

Applied with regime multiplier:

```
effective_deploy = base_deploy × regime_multiplier(regime)
```

| Regime | Multiplier |
|---|---|
| Panic dump (within bull) | 1.5–2.0 |
| Sideways | 1.0 |
| Bull trend | 0.8 |
| Bear trend | 0.3–0.5 |
| Blowoff top | 0.0 (no buys) |

Hard caps:
- `daily_deployment_cap` ≤ 5–10% of total portfolio
- No buy below `reserve_floor`
- No buy if kill switch active

## Sell Logic (gated)

**Definition of local low:** `A_local_low = rolling min(low, 48h)`, evaluated at the candle where rebound is detected. This anchor is fixed at detection time and does not update until a new sell cycle begins.

| Rebound from `A_local_low` | Base sell |
|---|---|
| +4% | 10% of trading BTC |
| +8% | 20% of trading BTC |
| +12% | 30% of trading BTC |

Gates (ALL must pass):
1. `price > avg_cost_fifo_lot × (1 + min_profit_threshold)` — checks the FIFO lot to be consumed, not global avg
2. Not in strong bull trend (regime_multiplier_sell applies)
3. Sell never touches core bucket
4. After sell, `trading_btc_qty` must remain ≥ `trading_floor` (expressed as % of total_portfolio)

Sell regime multipliers:

| Regime | Sell multiplier |
|---|---|
| Blowoff top | 1.5 |
| Bull trend | 0.3 |
| Sideways | 1.0 |
| Bear trend | 0.8 |
| Panic dump | 0.0 (no sells) |

## Core Promotion Rule

When `trading_btc_qty > trading_target × 1.3` for ≥7 days, the excess is promoted:

```
excess = trading_btc_qty − trading_target
core_btc_qty += excess
trading_btc_qty −= excess
```

> **[v2.1 NOTE]** The 7-day check is evaluated once per day at 00:00 UTC based on the end-of-day snapshot balance, not on intra-day ticks. This prevents race conditions from intra-day trading affecting the counter.

This is **how core grows** over time. Excess is then swept to cold storage.

---

# 11. Adaptive Grid System

Grid spacing adapts to realized volatility. Use **30-day annualized realized volatility (σ_ann)** for grid spacing, not raw `A_vol` (ATR ratio).

```
σ_ann = std(daily_log_returns, window=30) × sqrt(365)
```

| Volatility regime (σ_ann) | Grid spacing (per level) |
|---|---|
| Low (< 40%) | 1–2% |
| Medium (40–80%) | 3–5% |
| High (> 80%) | 6–10% |

Grid is rebuilt when:
- Volatility regime changes (hysteresis to avoid flapping)
- Range anchor moves > 10%
- Regime classifier changes state

---

# 12. Regime Detection Layer

## Labeling Approach: Unsupervised Only

No human-labeled "panic" vs "bear" training data. Methods:

1. **HMM (3-state or 5-state)** on log-returns + realized vol
   - Use 3-state HMM as baseline; optionally expand to 5-state if validation improves
   - Cluster indices are post-hoc mapped to semantic regimes based on centroid analysis
2. **K-means clustering** on feature vector
3. **Change-point detection** (Bayesian / BOCPD) for regime transitions

> **[v2.1 NOTE]** The system defines 5 semantic regimes. HMM state count does not need to equal 5 — use the state count that produces the most stable classification (validated via AIC/BIC). Post-hoc semantic mapping from cluster indices to regime names is required after each retraining.

Output regimes (emitted labels are just indices; human names come from post-hoc analysis):

| Regime | Typical features |
|---|---|
| Panic dump | Negative returns, high vol, funding negative, volume spike |
| Sideways | Low vol, range-bound, flat trend |
| Bull trend | Positive trend slope, rising OI, positive funding |
| Blowoff top | Extreme funding, very high vol, parabolic price |
| Bear market | Negative trend, declining OI, low volume |

## Features

**Basic:**
- ATR, realized vol (multiple windows)
- MA slope (EMA20, EMA50, EMA200)
- RSI regime
- Volume z-score

**Advanced:**
- Funding rate (perp)
- Open interest delta
- Liquidation data
- Orderflow / delta volume
- Volume profile / POC distance

---

# 13. AI Integration Strategy

## NOT used for:

```
Predicting exact BTC price direction.
```

## Used for:

### A. Regime classification
Unsupervised, outputs state + confidence.

### B. Dynamic position sizing
`confidence → deployment multiplier (0.5 – 1.5)`

### C. Adaptive grid optimization
RL adjusts grid spacing, reserve usage, rebound thresholds within bounded action space.

---

# 14. Reinforcement Learning Strategy

## What RL optimizes

| Component | RL target |
|---|---|
| Grid spacing multiplier | Yes |
| Reserve deployment curve | Yes |
| Sell ratio by regime | Yes |
| Profit threshold | Yes |
| Raw price prediction | **No** |

## Data Budget Problem

BTC has ~15 years of daily data, only a handful of truly distinct regimes. RL typically needs 10⁵–10⁶ episodes. Options:

1. **Synthetic market simulator** (required for Phase 4):
   - GBM with regime-switching volatility
   - GAN / diffusion-based generator trained on historical features
   - Validate simulator: generated series must pass stylized-fact tests (fat tails, vol clustering, autocorr of |r|)
2. **Bounded action space**: ≤ 4 continuous parameters to keep sample complexity tractable
3. **Offline RL** (CQL, IQL) on historical data as warm start before online fine-tuning in simulator

---

# 15. Reward Function

## Bad
```python
reward = usdt_profit
```

## Good
```python
reward = (
    btc_growth                     # primary
    - drawdown_penalty             # survival
    - overtrading_penalty          # fees + taxes
    - reserve_depletion_penalty    # liquidity
    - invariant_violation_penalty  # huge negative, terminal
    - hodl_underperformance_penalty  # must beat baseline
)
```

`hodl_underperformance_penalty` is the key addition: if strategy underperforms passive HODL over the episode, punish.

---

# 16. State Representation

```python
state = [
    # Price & vol
    btc_price,
    returns_1h, returns_24h, returns_7d,
    realized_vol_short, realized_vol_long,
    atr_normalized,

    # Trend
    ema20_slope, ema200_slope,
    price_vs_ema200,

    # Derivatives
    funding_rate,
    oi_delta,
    liquidation_intensity,

    # Regime
    regime_label_onehot,
    regime_confidence,

    # Portfolio (normalized)
    core_btc_ratio,
    trading_btc_ratio,
    reserve_ratio,
    avg_cost_distance,          # (price - avg_cost_fifo_lot) / avg_cost_fifo_lot
    unrealized_pnl_btc,

    # Constraints
    daily_capacity_remaining,
    reserve_headroom,
]
```

---

# 17. Risk Overlay & Kill Switches

## Standing Rules

| Rule | Value |
|---|---|
| Max daily deployment | 5–10% of portfolio |
| Min USDT reserve | 10–20% of portfolio |
| Core BTC: never sell / never leverage | Enforced by INV-1 |
| Max BTC on hot exchange | 25% of total BTC |

## Kill Switches (automatic pause)

**Drawdown definition:** Percentage decline from portfolio value at 00:00 UTC at the start of the rolling window (24h or 7d). Evaluated in BTC-equivalent terms at current BTC price.

| Trigger | Action |
|---|---|
| Drawdown > 15% in 24h (vs 00:00 UTC snapshot) | Pause new buys, alert |
| Drawdown > 25% in 7d (vs 00:00 UTC 7 days ago) | Pause all trading, manual resume |
| Reserve < floor | Pause buys only |
| Exchange API error rate > 5% in 5 min | Pause all, alert |
| Stablecoin depeg > 2% | Freeze affected stable, rebalance |
| Spread > 5× 30-day median | Pause all |
| Funding rate > 0.3%/8h | Pause aggressive buys |
| Fill slippage > 2% (vs mid-price at order placement) | Halt, reconcile |

## Circuit Breaker Reset

- Automatic: after condition clears for 30 min (soft triggers)
- Manual: any kill switch triggered twice in 24h requires human resume

---

# 18. Optional: Delta-Neutral Funding Harvest Sleeve

Separate, optional module (off by default until Phase 5+).

Mechanism:
- When `funding_rate_perp > threshold` (e.g., 0.05%/8h sustained)
- Open equal `short perp + long spot` → delta-neutral
- Collect funding in USDT → adds to reserve

Constraints:
- Max 20% of portfolio in this sleeve
- Requires separate risk monitor (basis risk, perp liquidation)
- Accounted for separately; BTC qty on spot side counts toward BTC inventory

This is a real accumulation engine (earns yield without changing BTC exposure) but adds complexity. Defer until core system is stable.

---

# 19. Fees, Taxes, and Slippage

## Fee Model (must be in backtest)

| Component | Default |
|---|---|
| Taker fee | 0.10% (Binance spot) |
| Maker fee | 0.02% (with BNB discount) |
| Assumed maker/taker mix | 60/40 |
| Slippage (per order) | 0.05% + f(size, book depth) |
| Withdrawal fee | Fixed, modeled per sweep |

**Round-trip cost assumption: ~0.25%.** A swing must clear at least 2× this to be worth taking.

## Slippage Measurement

> **[v2.1 FIX]** Slippage is defined as deviation from the **mid-price at order placement time**, not from the limit price. Limit orders execute at limit price or better, so measuring vs limit price always yields zero — which is meaningless.

```
slippage = |executed_price - mid_price_at_placement| / mid_price_at_placement
```

This correctly captures market impact and timing cost for both limit and market orders.

## Tax Model

- Each sell is a taxable event in most jurisdictions
- Passive HODL benchmark pays tax only on terminal sale
- Add `tax_drag` parameter (configurable by jurisdiction; default: short-term rate applied to realized gains per year)
- Backtest must report both **pre-tax** and **after-tax** BTC accumulation

## Tax Reporting Requirements

> **[v2.1 ADD]** The FIFO ledger must support tax export. Required outputs:

- Per-sell record: `(sell_date, sell_price, sell_qty, lot_purchase_date, lot_purchase_price, realized_pnl_usd, holding_period_days)`
- Annual summary: total realized gains (short-term vs long-term by jurisdiction threshold)
- Export format: CSV compatible with standard crypto tax tools (Koinly, CoinTracker schema)
- Jurisdiction parameter in config; default assumes short-term = held < 365 days

## Sensitivity Analysis (required)

Run full backtest at:
- Fee levels: 0.05%, 0.10%, 0.15%
- Slippage: 0.02%, 0.05%, 0.10%
- Tax drag: 0%, 20%, 35%

If strategy fails to beat HODL at 0.10% / 0.05% / 20%, it is not viable.

---

# 20. Anti-Overfitting Methodology

## Validation Pipeline

```
Train
  ↓
Walk-Forward Validation
  ↓
CPCV (Combinatorial Purged Cross Validation)
  ↓
PBO (Probability of Backtest Overfitting)
  ↓
Out-of-Sample Backtest
  ↓
Paper Trading (≥3 months)
```

## Walk-Forward

Example schedule:
```
Train: 2018–2020 → Test: 2021
Train: 2018–2021 → Test: 2022
Train: 2018–2022 → Test: 2023
Train: 2018–2023 → Test: 2024
Train: 2018–2024 → Test: 2025 (paper)
```

## CPCV

- Purge and embargo around test fold boundaries
- Critical for crypto (autocorrelation, vol clustering)

## PBO

- Target: PBO < 0.5 (ideally < 0.3)
- If PBO > 0.7, strategy is almost certainly overfit

---

# 21. Benchmarks (Required)

Every backtest reports performance against:

| Benchmark | Why |
|---|---|
| Passive HODL (lump sum day 0) | **Primary**; ABAS must beat this in BTC terms net of tax |
| Weekly DCA (equal amount) | Naive strategy baseline |
| Fixed 5% grid (no regime) | Isolates value of regime/AI layer |
| Core + weekly DCA (no swing) | Isolates value of swing sleeve |

Report `Δ_BTC vs HODL` as headline metric for every run.

---

# 22. Backtesting Framework

## Stack

| Tool | Purpose |
|---|---|
| vectorbt | Fast sweep simulation |
| backtrader or nautilus-trader | Execution realism (order book, partial fills) |
| Polars / Pandas | Data processing |
| DuckDB | Ad-hoc analysis |
| MLflow | Experiment tracking |

## Backtest Requirements

- Must simulate partial fills
- Must model fees + slippage + withdrawal costs
- Must simulate funding payments (if funding sleeve enabled)
- Must reconcile invariants at every tick
- Must produce both pre-tax and after-tax metrics

---

# 23. Metrics

## BTC-Native (primary)

| Metric | Definition |
|---|---|
| `Δ_BTC vs HODL` | ABAS BTC qty − HODL BTC qty, at test end |
| BTC CAGR | Annualized BTC growth |
| BTC velocity | BTC accumulated per unit of risk (drawdown) |
| Core BTC growth rate | Rate of promotions to core |
| Reserve stability | % time reserve > floor |
| Max BTC drawdown | Peak-to-trough BTC qty |

## Secondary

- Sharpe / Sortino (in BTC terms, not USDT)
- Profit factor
- Recovery factor
- Trade count / month (overtrading check)
- Fee ratio (fees / gross profit)

---

# 24. Execution Architecture

```
src/
├── data/              # Ingestion, validation, cleaning
├── features/          # Feature engineering
├── regime/            # HMM, clustering, change-point
├── inventory/         # Core/trading/reserve state + cost basis
├── grid/              # Adaptive grid engine
├── risk/              # Invariants, kill switches
├── execution/         # Order routing, CCXT wrappers
├── portfolio/         # Portfolio tracking, reconciliation
├── backtest/          # vectorbt / backtrader harness
├── simulator/         # Synthetic market generator (Phase 4)
├── ai/                # RL agents, regime models
├── custody/           # Sweep logic, cold-storage reconciliation
├── monitoring/        # Metrics, Grafana exporters
├── api/               # Internal service API
└── tests/             # Unit + property-based + replay tests
```

---

# 25. Tech Stack

## Core

| Component | Tech |
|---|---|
| Language | Python 3.11+ |
| Exchange API | CCXT + direct Binance WS |
| Database | PostgreSQL |
| Time-series | TimescaleDB |
| Queue | Redis |
| Monitoring | Grafana |
| Metrics | Prometheus |
| Secrets | HashiCorp Vault or cloud KMS |

## AI

| Purpose | Tool |
|---|---|
| RL | Stable-Baselines3 / CleanRL |
| Experiment tracking | MLflow |
| Feature research | Qlib |
| Validation methodology | FinRL_Crypto |
| Architecture reference | FinRL-X |
| Market simulator | Custom + (optional) QuantGAN |

---

# 26. Data Sources

## Required

- Binance OHLCV (1m, 1h, 1d)
- Binance funding rate
- Binance OI
- Binance liquidation feed
- Volume profile

## Data Quality Pipeline (required before any backtest)

1. Gap detection (flag, don't silently fill)
2. Outlier detection (z-score + manual review queue)
3. Exchange outage periods marked and excluded
4. Forward-fill only for bounded gaps (<5 min)
5. Schema validation on every ingest

## Optional

- Fear & Greed Index
- ETF flows (post-2024)
- Macro calendar
- News sentiment (FinGPT)

---

# 27. Security

| Area | Requirement |
|---|---|
| API keys | Trade-only, withdrawal disabled, IP-whitelisted |
| Secrets storage | Vault / KMS; never in code or env files checked in |
| Cold storage | Hardware wallet or multisig for core |
| Hot exchange cap | Max 25% of total BTC |
| Log redaction | No keys/secrets in logs; redact ledger on share |
| Network | System runs behind VPN; exchange whitelist only |
| Audit log | Every order, every state change, immutable append-only |
| Disaster recovery | Portfolio state reproducible from exchange history + ledger |

---

# 28. Testing Strategy

## Unit Tests

- Inventory math (add/remove lot, cost basis calc)
- FIFO sell gating: verify INV-5 uses lot-level cost, not global avg_cost
- Regime classifier output shape and stability
- Grid rebuild determinism

## Property-Based Tests (hypothesis)

Invariants tested over random inputs:
- `INV-1`: no sequence of valid operations reduces core_btc
- `INV-3`: `abs(sum(buckets) - total_portfolio) < EPSILON` under all operations
- Cost basis is consistent under permutation of identical lots (FIFO-aware)
- Sell gate never allows a sell where lot cost > sell price after fees

## Replay Tests

- Full backtest over 2021, 2022, 2023, 2024 must produce deterministic output
- Snapshot test: portfolio state at specific dates must match committed expected values

## Chaos Tests (before live)

- Simulated exchange outage
- Simulated partial fill / rejected order
- Simulated stablecoin depeg
- Simulated data gap

---

# 29. Development Roadmap

## Phase 1 — Rule-Based Prototype

**Goal:** Build inventory engine, adaptive DCA, dynamic grid. **No AI.**

Deliverables:
- Cost basis tracker (FIFO, per-lot, tax-export ready)
- Portfolio state machine with invariants enforced
- Rule-based buy/sell logic
- Backtest harness with fee + slippage model

Exit criteria:
- All invariants hold across 5 years of historical replay
- Beats HODL in at least one full cycle (2020–2023) at 0.10% fees

## Phase 2 — Historical Backtesting

Test across:

| Cycle | Test of |
|---|---|
| 2018–2019 | Bear + early recovery |
| 2020–2021 bull | Euphoria |
| 2022 bear | Survival |
| 2023 recovery | Transition |
| 2024 ETF | Institutional flow |

Exit criteria:
- `Δ_BTC vs HODL` > 0 in ≥3 of 5 cycles after fees + tax
- Max BTC drawdown < HODL max drawdown

## Phase 3 — AI Overlay

Add:
- HMM / clustering regime classifier
- Regime-conditional sizing
- Still rule-based core logic

Exit criteria:
- Regime classifier stable (no flapping)
- Improves `Δ_BTC vs HODL` by ≥20% vs Phase 2

## Phase 4 — RL Optimization

Use RL for:
- Grid spacing
- Reserve deployment curve
- Sell ratio

Requirements:
- Market simulator passes stylized-fact tests
- Offline RL warm start
- PBO < 0.5

## Phase 5 — Paper Trading

- Live data, simulated execution
- Minimum 3 months, preferably 6
- Track: latency, slippage (vs mid-price at placement), fill quality vs model

Exit criteria:
- Live paper performance within 20% of backtest expectation
- No invariant violations
- No kill switch misfires

## Phase 6 — Small Capital Deployment

- Start: ≤1% of intended AUM
- Scale only after 3 months of live behavior matching paper
- Monthly review before any scale-up

## Phase 7 — Delta-Neutral Sleeve (Optional)

Only after Phase 6 is stable.

---

# 30. Failure Mode Playbook

| Failure | Trigger | Response |
|---|---|---|
| Overtrading | Trades/month > threshold OR fee ratio > 20% | Widen grid, raise profit threshold, reduce sell multiplier |
| Selling too much BTC | `trading_btc_qty` falls below floor | Halt sells, review sell-gating |
| Overfitting | Live underperforms backtest by > 30% over 3 months | Revert to Phase N-1, retrain with more purging |
| No reserve at dip | Reserve < floor during drawdown | Pause buys, audit deployment curve, confirm regime multipliers |
| Stablecoin depeg | Peg deviation > 2% | Freeze affected stable, rebalance to peg-stable |
| Exchange failure | API errors > 5% / 5 min | Kill switch, route to backup (Phase 5+) |
| Regulatory event | Exchange restricted in jurisdiction | Withdraw trading BTC to cold, pause system |
| Model drift | Regime classifier confidence collapses | Fallback to rule-only mode |
| Invariant violation | Any INV-* fails | Immediate halt, alert, manual review required |

Every failure mode has a named, pre-agreed response. No improvisation in production.

---

# 31. Common Failure Modes (diagnostic)

## F1 — Overtrading
- Symptoms: excessive churn, fee bleed, BTC qty declining despite positive USDT P&L
- Cure: profit threshold ↑, grid spacing ↑

## F2 — Selling Too Much BTC
- Symptoms: USDT balance growing, BTC qty falling, missed bull rides
- Cure: sell regime multipliers ↓ in bull regimes, trading_floor ↑

## F3 — Overfitting
- Symptoms: great backtest, poor live
- Cure: tighter validation, smaller action space, longer paper period

## F4 — No Reserve Management
- Symptoms: reserve exhausted early in drawdown, no capacity left for real bottom
- Cure: ladder deployment curve, regime multiplier, hard floors

---

# 32. AI Architecture Summary

## Recommended

```
Rule-Based Core
    +
HMM / Unsupervised Regime Detection
    +
RL Optimization Layer (bounded params)
    +
Risk Overlay + Invariants + Kill Switch
```

## Not Recommended

```
End-to-End Autonomous AI Trader
```

Unstable, unexplainable, and when it breaks, it breaks silently.

---

# 33. How FinRL Ecosystem Fits

| Project | Role |
|---|---|
| FinRL | RL foundation |
| FinRL_Crypto | Validation methodology (CPCV, PBO) |
| FinRL-X | Modular architecture reference |
| FinGPT | Sentiment / narrative feature (optional) |
| LangGraph | Agent orchestration (optional) |

---

# 34. Strategic Insight

The system behaves like:

```
A disciplined BTC inventory manager.
```

NOT:

```
A hyperactive prediction machine.
```

---

# 35. Ultimate Goal

```
Maximize BTC ownership across multiple market cycles,
net of fees and taxes,
measurably beating passive HODL in BTC terms,
while preserving capital through volatility and counterparty risk.
```

That, and only that, is the edge.
