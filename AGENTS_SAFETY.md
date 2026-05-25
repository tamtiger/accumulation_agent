# AGENTS_SAFETY.md — Global Safety Rules, Invariants & Kill Switches

> **Read every tick.** These rules apply to ALL agents without exception. Any violation halts the system.

---

## 1. Global Safety Rules

1. **State Immutability:** No agent writes directly to the portfolio database. All state mutations are proposed as signed payload schemas and sent to the Inventory Agent via the Orchestrator.

2. **Strict Tick Serialization:** Every tick follows a single-threaded chronological flow. No parallel agent executions on the same account instance:
   ```
   Data → Feature → Regime → Inventory → Grid → Risk → Execution → Portfolio → Inventory (update) → Monitoring
   ```

3. **Fail-Safe Heartbeat:** Every agent emits a heartbeat to Redis (`heartbeat:<agent_name>`) every 10 seconds. If missing for > 30 seconds, the Orchestrator triggers an emergency halt.

4. **No Hallucinations:** On missing data or API failure, agents MUST NOT generate synthetic values or estimates. Report the data gap immediately and trigger a soft halt.

5. **Structured Logging:** Every log entry must contain `timestamp`, `agent_name`, `tick_id`, `action`, `state_snapshot`, `metadata`. Redact all secrets. Log price, size, and slippage for every executed fill.

---

## 2. Invariants (Hard Asserts — violation = immediate HALT)

| ID | Rule | Implementation note |
|---|---|---|
| `INV-1` | `core_btc_qty` is monotonically non-decreasing | Any code path that could reduce it is a critical bug |
| `INV-2` | `reserve_usdt >= reserve_floor` (% of portfolio) | Check against current portfolio value, not nominal |
| `INV-3` | `abs(sum(buckets) - total_portfolio) < 1e-8 BTC` | Strict equality is infeasible due to float, partial fills, unsettled fees |
| `INV-4` | No order placed if it would violate INV-1 or INV-2 | Pre-check before submitting to Risk Agent |
| `INV-5` | No sell if `price < avg_cost_fifo_lot × (1 + min_profit_threshold)` | Use FIFO queue head lot cost — NOT global `avg_cost_portfolio` |
| `INV-6` | `daily_deployed_capital <= daily_deployment_cap` | Resets at 00:00 UTC |
| `INV-7` | `total BTC on hot exchange <= hot_exchange_cap` | 25% of total portfolio value |

**INV-3 note:** `sum(buckets)` = `core_btc_qty` (in BTC) + `trading_btc_qty` (in BTC) + `reserve_usdt / btc_price`. All converted to BTC for comparison.

**INV-5 note:** `avg_cost_fifo_lot` = purchase price of the lot currently at the head of the FIFO queue — the specific lot that will be consumed by the next sell. Do NOT use the weighted average across all lots.

---

## 3. Kill Switches (Automatic HALT triggers)

**Drawdown definition:** Percentage decline from portfolio BTC-equivalent value at 00:00 UTC at the start of the rolling window.

| Trigger | Threshold | Action |
|---|---|---|
| Drawdown (24h) | > 15% | Pause new buys, alert operators |
| Drawdown (7d) | > 25% | Pause all trading, require manual resume |
| Reserve below floor | `reserve_usdt < reserve_floor` | Pause buys only |
| Exchange API error rate | > 5% in any 5-minute window | Pause all, alert |
| Stablecoin depeg | > 2% deviation (USDT/USDC/DAI) | Freeze affected stable, rebalance |
| Bid-ask spread | > 5× 30-day median | Pause all |
| Funding rate | > 0.3%/8h | Pause aggressive buys |
| Fill slippage | > 2% vs mid-price at placement | Halt, reconcile |

---

## 4. HALT Procedure

When any kill switch fires:

1. Cancel **all** open orders on the exchange immediately
2. Disable all automated order placement
3. Broadcast emergency alert via Telegram + SMS to all registered operators (include error payload and traceback)
4. Lock system state — require manual CLI input to resume

**Circuit Breaker Reset:**
- **Soft reset:** Auto-resume after condition clears for ≥ 30 continuous minutes
- **Hard reset:** If a kill switch fires twice within 24 hours → freeze, require manual resume only

---

## 5. Architectural Safety Boundaries

These boundaries must never be crossed without a design review:

- **Risk Agent is the only order approver.** Grid Agent proposes. Risk Agent decides. No agent bypasses this gate.
- **Inventory Agent is the only ledger writer.** `fifo_lots` and `portfolio_snapshots` are read-only for all other agents.
- **Config is immutable per run.** `config/production.json` loads once at startup. No hot-reload mid-run.
- **`core_btc_qty` only increases.** Any code path that could reduce it is a critical bug requiring immediate halt.
