# AGENTS_SPECS.md — Agent Execution Specifications

> Load this file for the agent role you are executing. Follow rules exactly.

---

## 1. Data Ingestion & Validation Agent

**Role:** Fetch raw market inputs. Produce validated, clean time-series records. Identify anomalies before data reaches downstream agents.

**Rules:**

1. **Gap Detection:** If `timestamp_delta > expected_interval`, trigger a Data Gap Event and notify the Orchestrator. Do not forward the tick.

2. **Outlier Filtering:**
   ```
   z = (x - μ) / σ   [rolling window = 100 periods]
   ```
   If `|z| > 4.5` → quarantine tick in DB, do not pass to Feature Agent.

3. **Schema Enforcement:** All fields must be non-null and correctly typed:
   `timestamp, open, high, low, close, volume, funding_rate, open_interest, liquidations`
   Fail the tick immediately on any schema violation.

---

## 2. Feature Engineering Agent

**Role:** Compute technical indicators, rolling anchors, and the annualized volatility used by the Grid Agent.

**Rules:**

1. **Anchors — compute every tick:**
   - `A_trend` = EMA(200, daily) — macro trend filter
   - `A_range` = rolling max(high, 30d) — drawdown-from-peak trigger
   - `A_vol` = ATR(14) / price — volatility proxy only; do NOT use for grid spacing
   - `A_mean` = EMA(20, 4h) — mean-reversion anchor
   - `A_local_low` = rolling min(low, 48h) — fixed at rebound detection candle; do not update mid-cycle

2. **Annualized Volatility (σ_ann) — pass to Grid Agent:**
   ```
   σ_ann = std(daily_log_returns, window=30) × sqrt(365)
   ```
   This is the only value used for grid spacing. `A_vol` is a proxy; `σ_ann` is authoritative.

3. **State Vector — compute every tick:**
   - EMA slopes: EMA(20), EMA(50), EMA(200) over 4h and 1d
   - Funding rate + OI delta (24h)
   - Volume z-score (30d window)
   - RSI(14) + liquidation intensity

4. **Output validation:** Feature vector must be complete, non-null, and schema-valid before forwarding.

---

## 3. Market Regime Detection Agent

**Role:** Classify the current Bitcoin market regime using unsupervised models. Output regime label + confidence score every tick.

**Rules:**

1. **Classification Pipeline:**
   - **HMM:** Use 3-state as baseline. Optionally evaluate 5-state. Select via AIC/BIC. Do NOT force state count to equal 5 — semantic mapping is post-hoc.
   - **K-means** on feature vector
   - **BOCPD** for change-point detection

   Post-hoc semantic mapping (re-validate after every retraining):

   | Regime | Typical features |
   |---|---|
   | `Panic Dump` | Negative returns, high vol, volume spike, negative funding |
   | `Sideways` | Flat trend, low vol, flat funding |
   | `Bull Trend` | Positive EMA slopes, rising OI, positive funding |
   | `Blowoff Top` | Parabolic price, extreme positive funding, hyper-vol |
   | `Bear Market` | Negative EMA slopes, declining OI, declining volume |

2. **Hysteresis Filter:** New regime must hold for ≥ 3 consecutive 4h candles before updating DB state. Exception: confidence score `> 0.95` allows immediate update.

3. **Confidence Score:** Output `C ∈ [0.0, 1.0]`. If `C < 0.40` → fallback to `Sideways` sizing rules.

---

## 4. Inventory Management & Cost-Basis Agent

**Role:** Single source of truth for portfolio state. Track FIFO cost basis. Enforce core promotion rule. Only agent that writes to the ledger.

**Rules:**

1. **Bucket tracking (persist to DB):**
   - `core_btc_qty` — cold storage, never sold
   - `trading_btc_qty` — hot exchange
   - `reserve_usdt` — stablecoin reserve (USDT + USDC + DAI)

2. **FIFO Ledger:**
   - **On BUY:** Append `(lot_id, qty, purchase_price, timestamp, regime_tag)` to FIFO queue tail
   - **On SELL:** Consume from FIFO queue head (oldest first). Compute realized P&L:
     ```
     realized_pnl = Σ (sell_price - lot_purchase_price) × lot_qty
     ```
   - After each operation, recompute both cost metrics:
     ```
     avg_cost_fifo_lot   = purchase_price of current FIFO queue head
                           → used by INV-5 sell gating
     avg_cost_portfolio  = Σ(lot_qty × lot_price) / Σ lot_qty
                           → used for state reporting and RL state vector
     ```
   - Export sell records for tax reporting: `(sell_date, sell_price, sell_qty, lot_purchase_date, lot_purchase_price, realized_pnl_usd, holding_period_days)`
   - `holding_period_days` = `sell_date - lot_purchase_date`. Short-term if < 365 days (configurable by jurisdiction).

3. **Core Promotion Rule:**
   - Evaluated **once per day at 00:00 UTC** on end-of-day snapshot balance. Never intra-day — avoids race conditions with active trading.
   - If `trading_btc_qty > trading_target × 1.3` for 7 consecutive daily checks:
     ```
     excess = trading_btc_qty - trading_target
     core_btc_qty += excess
     trading_btc_qty -= excess
     ```
   - Emit Promotion Signal → prompt manual sweep to whitelisted cold wallet address.

---

## 5. Adaptive Grid Agent

**Role:** Compute proposed buy/sell order grid using volatility, regime, and anchors. All orders are unsigned proposals — Risk Agent approves.

**Rules:**

1. **Grid Spacing** — use `σ_ann` from Feature Agent:

   | σ_ann | Grid spacing per level |
   |---|---|
   | < 40% | 1% – 2% |
   | 40% – 80% | 3% – 5% |
   | > 80% | 6% – 10% |

2. **Buy Sizing:**
   Base deploy from `A_range` drawdown:

   | Drawdown from A_range | Base reserve deploy |
   |---|---|
   | −3% | 5% |
   | −6% | 10% |
   | −10% | 20% |
   | −15% | 30% |
   | −25% | 40% |

   Apply regime multiplier:

   | Regime | Buy multiplier |
   |---|---|
   | Panic Dump | 1.5 – 2.0 |
   | Sideways | 1.0 |
   | Bull Trend | 0.8 |
   | Bear Trend | 0.3 – 0.5 |
   | Blowoff Top | 0.0 (buys disabled) |

   ```
   effective_deploy = base_deploy × regime_multiplier
   ```

3. **Sell Gating** — ALL conditions must pass before proposing a sell:

   `A_local_low` = `rolling min(low, 48h)`, fixed at the candle where rebound is first detected. Do not update mid-cycle.

   | Rebound from A_local_low | Base sell |
   |---|---|
   | +4% | 10% of trading BTC |
   | +8% | 20% of trading BTC |
   | +12% | 30% of trading BTC |

   Apply regime multiplier:

   | Regime | Sell multiplier |
   |---|---|
   | Blowoff Top | 1.5 |
   | Bull Trend | 0.3 |
   | Sideways | 1.0 |
   | Bear Trend | 0.8 |
   | Panic Dump | 0.0 (sells disabled) |

   Pre-flight checks (suppress order if any fail):
   - `target_sell_price >= avg_cost_fifo_lot × (1 + min_profit_threshold)` — FIFO head lot cost, not portfolio avg
   - `trading_btc_qty` after sell remains `≥ trading_floor` (trading_floor = % of total_portfolio)
   - Sell never touches `core_btc_qty`

---

## 6. Risk Overlay & Invariant Agent

**Role:** Final safety gate before any order reaches the exchange. Validate all invariants. Trigger HALT on violation. No bypass exists.

**Rules:**

1. **Invariant Verification** — check all 7 against proposed order array:
   - `INV-1`: `core_btc_qty` does not decrease
   - `INV-2`: `reserve_usdt` stays ≥ `reserve_floor` after order
   - `INV-3`: `abs(sum(buckets) - total_portfolio) < 1e-8 BTC`
   - `INV-4`: Reject any order that would violate INV-1 or INV-2
   - `INV-5`: Reject sell if `price < avg_cost_fifo_lot × (1 + min_profit_threshold)`
   - `INV-6`: Cumulative daily deploy ≤ `daily_deployment_cap`
   - `INV-7`: Total exchange BTC ≤ `hot_exchange_cap`

2. **Kill Switch Monitoring:** See `AGENTS_SAFETY.md` §3 for full trigger table and §4 for HALT procedure. On any trigger → execute HALT immediately.

---

## 7. Execution Agent

**Role:** Submit approved orders to Binance via CCXT. Track fills. Log slippage. Handle rate limits.

**Rules:**

1. **Order Submission:** Submit only orders approved by the Risk Agent via the Orchestrator. No exceptions.

2. **Size Rounding:** Round size and price to exchange `lotSize` and `tickSize` using `ROUND_DOWN`. Never submit below minimum order size (10 USDT on Binance spot).

3. **Fill Tracking:** Monitor order status via WebSocket. Report partial fills to Orchestrator immediately with filled quantity.

4. **Slippage Logging:**
   Record `mid_price_at_placement` at the moment the order is submitted.
   ```
   slippage = |executed_price - mid_price_at_placement| / mid_price_at_placement
   ```
   Do NOT measure vs limit price — limit orders always fill at or better than limit price, making that measure zero and useless.

   If `slippage > 2%` → trigger Risk Agent HALT event immediately.

---

## 8. Portfolio Tracking Agent

**Role:** Monitor bucket allocations in real-time. Reconcile exchange balances vs DB after every fill.

**Rules:**

1. **Reconciliation:** After every fill, compare exchange-reported balances with DB buckets. If discrepancy `> 0.01%` → flag Ledger Discrepancy Event, notify Orchestrator.

2. **Daily Audit:** At 00:00 UTC, reconcile local DB transaction log against exchange REST API balance and trade history.

3. **Exposure Monitor:**
   ```
   exchange_exposure = (trading_btc_qty × btc_price) / total_portfolio_value
   ```
   If `> 25%` (INV-7 threshold) → emit warning to Risk Agent.

---

## 9. Monitoring & Alerting Agent

**Role:** Export metrics. Audit heartbeats. Dispatch emergency alerts.

**Rules:**

1. **Prometheus Export:** Agent loop latencies, DB write status, API rate limit usage, slippage, portfolio balances.

2. **Heartbeat Audit:** If any `heartbeat:<agent_name>` key missing for > 30s → send panic event to Orchestrator.

3. **Emergency Dispatch:** On HALT signal → broadcast Telegram + SMS to all operators immediately with error payload + traceback link.

---

## 10. Orchestrator Agent

**Role:** Manage the tick execution graph. Coordinate state snapshots, error handling, and message passing between all agents.

**Rules:**

1. **Tick Trigger:** Initiate sequential execution loop on cron tick or WebSocket update.

2. **State Persistence:** Save serialized JSON snapshot of all agent states, balances, and parameters to TimescaleDB at end of every tick.

3. **Circuit Breaker Recovery:**
   - Soft reset: Auto-resume after trigger condition clears for ≥ 30 continuous minutes
   - Hard reset: Kill switch fires twice in 24h → freeze, require manual CLI resume

4. **Bootstrapping Phases:**

   | Phase | Duration | Action |
   |---|---|---|
   | B1 — Seed | Week 1 | Deploy 20% of total planned capital immediately (market buys, split core seed + trading floor) |
   | B2 — DCA Ramp | Weeks 2–12 | Deploy 60% of total planned capital via weekly DCA (~6% of remaining per week) until core reaches 60–80% |
   | B3 — Opportunistic | Weeks 4–26 | Reserve 20% of total planned capital for dips >1σ below 90-day mean; full adaptive system active |
