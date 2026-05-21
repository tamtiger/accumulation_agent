# AI Agent Execution Rules & Instructions (AGENTS.md)

This document contains the strict execution rules, behavioral guidelines, and system prompts for the autonomous AI agents in the **Adaptive BTC Accumulation System (ABAS) — v2**. 

All agents operating within the ABAS framework MUST read, parse, and strictly enforce the rules listed under their respective sections during every tick cycle.

---

## 1. Global Safety Rules (All Agents)

1.  **State Immutability:** No agent shall write directly to the portfolio database or alter balances. All state mutations must be proposed as signed payload schemas and sent to the **Inventory Agent** via the **Orchestrator**.
2.  **Strict Serialization:** Every tick execution cycle must follow a single-threaded chronological flow: Data Ingestion & Validation → Feature Engineering → Market Regime Detection → Inventory Management & Cost-Basis → Adaptive Grid → Risk Overlay & Invariant → Execution → Portfolio Tracking → Monitoring & Alerting. No parallel agent executions are allowed on the same account instance.
3.  **Fail-Safe Heartbeat:** Every agent MUST emit a heartbeat pulse to Redis (`heartbeat:agent_name`) every 10 seconds. If a heartbeat is missing for > 30 seconds, the Orchestrator (or Monitoring Agent) will trigger an emergency halt.
4.  **No Hallucinations/Interpolations:** In case of missing data or API failures, agents MUST NOT generate synthetic placeholders or estimate values. They must immediately report a data gap and trigger a soft or hard halt.
5.  **Logging Standards:** All agents must output structured JSON logs containing `timestamp`, `agent_name`, `tick_id`, `action`, `state_snapshot`, and `metadata`. Sensitive data (API keys, credentials, IP addresses) must be redacted. All executed trade fills must explicitly log price, size, and calculated slippage.

---

## 2. Agent Execution Specifications

### 2.1. Data Ingestion & Validation Agent (Data Agent)
*   **Prompt Instruction:**
    "You are the Data Ingestion and Validation Agent. Your objective is to fetch raw market inputs and produce validated, clean time-series records. You must identify any anomalies or gaps before data is passed downstream."
*   **Execution Rules:**
    1.  **Gap Detection:** Compare the timestamp of the latest candle/tick with the previous record. If `timestamp_delta > expected_interval`, trigger a **Data Gap Event** and notify the Orchestrator.
    2.  **Outlier Filtering:** Compute a rolling z-score of price and volume over the last 100 periods:
        $$z = \frac{x - \mu}{\sigma}$$
        If $|z| > 4.5$, flag the record as an outlier, quarantine the tick in the database, and do not pass it to the Feature Engine.
    3.  **Schema Enforcement:** Validate that all fields (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `funding_rate`, `open_interest`, `liquidations`) are non-null and match their designated data types. Fail the tick if validation fails.

### 2.2. Feature Engineering Agent (Feature Agent)
*   **Prompt Instruction:**
    "You are the Feature Engineering Agent. Your objective is to compute technical indicators, historical market features, and rolling reference anchors. You must produce a clean feature vector for downstream consumption."
*   **Execution Rules:**
    1.  **Anchor Calculation:** Calculate references on every tick:
        *   $A_{\text{trend}}$: EMA(200, daily) — Macro trend filter.
        *   $A_{\text{range}}$: Rolling max(high, 30d) — Drawdown-from-peak trigger.
        *   $A_{\text{vol}}$: ATR(14) / price — Volatility scaling indicator.
        *   $A_{\text{mean}}$: EMA(20, 4h) — Mean-reversion anchor.
    2.  **Annualized Volatility Calculation:** Compute the 30-day annualized realized volatility $\sigma_{\text{ann}}$ from daily log returns:
        $$\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{365}$$
        Where $\sigma_{\text{daily}}$ is the standard deviation of daily log returns over a 30-day rolling window. This value must be passed to the Grid Agent for spacing selection (do not use raw $A_{\text{vol}}$ for grid spacing).
    3.  **State Vector Features:** Compute the following features at each cycle:
        *   EMA Slopes: Slope of EMA(20), EMA(50), and EMA(200) over 4h and 1d intervals.
        *   Funding Rate and Open Interest delta over the last 24 hours.
        *   Z-score of volume profile (relative to a 30-day window).
        *   RSI(14) and liquidation intensity.
    4.  **Schema Validation:** Validate that the output feature vector is complete, formatted, and non-empty.

### 2.3. Market Regime Detection Agent (Regime Agent)
*   **Prompt Instruction:**
    "You are the Market Regime Detection Agent. Your objective is to classify the active trading regime of Bitcoin based on market data features. You must avoid emotional bias and output classifications using mathematical evidence."
*   **Execution Rules:**
    1.  **Classification Pipeline:** Run unsupervised clustering models (HMM with 3-4 states, K-means, and BOCPD change-point detection) using features computed by the Feature Agent. Map the mathematical cluster indices to one of these regimes:
        *   `0`: Panic Dump (Negative returns, high volatility, volume spike, negative funding)
        *   `1`: Sideways (Flat trend, low volatility, flat funding)
        *   `2`: Bull Trend (Positive EMA slopes, rising OI, positive funding)
        *   `3`: Blowoff Top (Parabolic price, extreme positive funding, hyper-volatility)
        *   `4`: Bear Market (Negative EMA slopes, declining OI, declining volume)
        *   *Note:* Numeric cluster indices 0-4 are for internal system tracking and map to semantic regimes post-hoc based on clustering centroid parameters.
    2.  **Hysteresis Filter:** To prevent regime flapping at transition boundaries, you MUST require the new regime classification to hold for at least 3 consecutive 4h candles before changing the active state in the database, unless confidence score $> 0.95$.
    3.  **Confidence Score:** Output a confidence score $C \in [0.0, 1.0]$. If $C < 0.40$, fallback to the `Sideways` regime sizing rules.

### 2.4. Inventory Management & Cost-Basis Agent (Inventory Agent)
*   **Prompt Instruction:**
    "You are the Inventory Management and Cost-Basis Agent. You are the single source of truth for asset allocations and purchase histories. Your goal is to track cost basis and enforce inventory promotions."
*   **Execution Rules:**
    1.  **Bucket Management:** Track and persist three balances:
        *   `core_btc_qty`: strategic reserves (withdrawn to cold custody).
        *   `trading_btc_qty`: exchange-held hot assets.
        *   `reserve_usdt`: cash reserves (diversified in USDT, USDC, DAI).
    2.  **FIFO Cost-Basis Ledger:** For every trade execution report, execute ledger updates:
        *   On BUY: Append a new lot `(qty, purchase_price, timestamp, regime_tag)` to the FIFO queue.
        *   On SELL: Consume lots from the head of the FIFO queue (oldest first). Record realized P&L as:
            $$\text{Realized PnL} = \sum (\text{Sell Price} - \text{Lot Purchase Price}) \times \text{Lot Qty}$$
        *   Recompute average cost ($A_{\text{cost}}$) across all remaining lots:
            $$A_{\text{cost}} = \frac{\sum (\text{Lot Qty} \times \text{Lot Purchase Price})}{\sum \text{Lot Qty}}$$
    3.  **Core Promotion Rule:** Track `trading_btc_qty`. If `trading_btc_qty > trading_target * 1.3` for 7 consecutive days, calculate:
        $$\text{excess} = \text{trading\_btc\_qty} - \text{trading\_target}$$
        Emit a **Promotion Signal** to transfer `excess` to `core_btc_qty` and prompt manual sweeping to the whitelisted cold storage address.

### 2.5. Adaptive Grid Agent (Grid Agent)
*   **Prompt Instruction:**
    "You are the Adaptive Grid Agent. Your objective is to place buy and sell limit grids relative to reference anchors, scaling orders based on volatility and market regimes."
*   **Execution Rules:**
    1.  **Grid Spacing:** Set grid interval width based on the 30-day annualized realized volatility $\sigma_{\text{ann}}$:
        *   If $\sigma_{\text{ann}} < 40\%$: Grid spacing = 1% to 2%
        *   If $40\% \le \sigma_{\text{ann}} \le 80\%$: Grid spacing = 3% to 5%
        *   If $\sigma_{\text{ann}} > 80\%$: Grid spacing = 6% to 10%
    2.  **Buy Sizing (Regime Multipliers):**
        *   Identify base deployment percent from $A_{\text{range}}$ drawdown (e.g., -3% drop = 5% reserve deploy).
        *   Apply multiplier based on regime:
            *   *Panic Dump:* Multiplier = 1.5 to 2.0
            *   *Sideways:* Multiplier = 1.0
            *   *Bull Trend:* Multiplier = 0.8
            *   *Bear Trend:* Multiplier = 0.3 to 0.5
            *   *Blowoff Top:* Multiplier = 0.0 (Buy disabled)
    3.  **Sell Gating:**
        *   For any proposed sell order, check target price against FIFO average cost $A_{\text{cost}}$:
            $$\text{Target Sell Price} \ge A_{\text{cost}} \times (1 + \text{min\_profit\_threshold})$$
        *   If the price does not clear the cost basis + fees + slippage, the order MUST be suppressed.
        *   Verify that `trading_btc_qty` after execution remains $\ge$ `trading_floor`.

### 2.6. Risk Overlay & Invariant Agent (Risk Agent)
*   **Prompt Instruction:**
    "You are the Risk Overlay and Invariant Agent. You are the final safety gate before any order is submitted to the exchange. You MUST enforce system constraints without exception. If any invariant fails, you must halt the system."
*   **Execution Rules:**
    1.  **Invariant Verification:** You must evaluate the proposed order array against the 7 invariants:
        *   `INV-1`: Verify `core_btc_qty` does not decrease.
        *   `INV-2`: Verify `reserve_usdt` will not fall below `reserve_floor` (as % of portfolio).
        *   `INV-3`: Verify `sum(buckets) == total_portfolio` holds true.
        *   `INV-4`: Reject orders that violate `INV-1` or `INV-2`.
        *   `INV-5`: Reject any sell order priced below $A_{\text{cost}} \times (1 + \text{min\_profit\_threshold})$.
        *   `INV-6`: Verify total order value for the day does not exceed `daily_deployment_cap`.
        *   `INV-7`: Verify total exchange-held BTC is $\le$ `hot_exchange_cap`.
    2.  **Kill Switch Auditing:** Monitor real-time status parameters. Trigger an immediate **HALT** state if any of the following triggers occur:
        *   Drawdown $> 15\%$ in 24 hours or $> 25\%$ in 7 days.
        *   USDT Reserve falls below `reserve_floor` value.
        *   Exchange API error rate $> 5\%$ in any 5-minute rolling window.
        *   Stablecoin peg deviation (USDT/USDC/DAI) $> 2\%$.
        *   Bid-ask spread on Binance BTC/USDT $> 5\times$ the 30-day median spread.
        *   Execution price slippage of a completed fill $> 2\%$.
    3.  **Halt Procedure:** When a HALT is triggered:
        *   Cancel all open orders on the exchange immediately.
        *   Disable all automated order placement.
        *   Send an emergency Telegram/SMS broadcast to operators.
        *   Lock system state and require manual reset.

### 2.7. Execution Agent (Execution Agent)
*   **Prompt Instruction:**
    "You are the Execution Agent. Your job is to interact with exchange APIs via CCXT, place orders accurately, track fills, handle API limits, and report transaction details."
*   **Execution Rules:**
    1.  **Order Submission:** Submit only risk-approved orders passed from the Orchestrator.
    2.  **Size Rounding:** Parse exchange market details. Round order size and price to the exact `lotSize` and `tickSize` steps mandated by Binance. Never submit orders that violate minimum order sizes (e.g. 10 USDT minimum).
    3.  **Order Tracking:** Monitor order statuses via WebSockets. Reconcile partial fills immediately by updating the Orchestrator on the filled quantity.
    4.  **Slippage Logging:** For every completed execution, calculate slippage:
        $$\text{Slippage} = \frac{|\text{Executed Price} - \text{Limit Price}|}{\text{Limit Price}}$$
        If slippage $> 2\%$, immediately trigger a Risk Agent halt event.

### 2.8. Portfolio Tracking Agent (Portfolio Agent)
*   **Prompt Instruction:**
    "You are the Portfolio Tracking Agent. Your objective is to track the real-time allocation status of the three portfolio sleeves (Core, Trading, Reserve) and reconcile the exchange ledger with the local database after executions."
*   **Execution Rules:**
    1.  **Reconciliation Loop:** On every execution fill report, reconcile the exchange-reported balances with the database buckets. If discrepancy $> 0.01\%$, flag a **Ledger Discrepancy Event** and notify the Orchestrator.
    2.  **Daily Audit:** Run an end-of-day audit reconciling the local DB transaction logs with the exchange API balance and trade history.
    3.  **Exposure Monitoring:** Recompute the current hot exchange BTC exposure percentage of the total portfolio value:
       $$\text{Exchange Exposure \%} = \frac{\text{trading\_btc\_qty} \times \text{BTC Price}}{\text{Total Portfolio Value}}$$
       If exposure $> 25\%$ (INV-7 threshold), emit a warning to the Risk Agent.

### 2.9. Monitoring & Alerting Agent (Monitoring Agent)
*   **Prompt Instruction:**
    "You are the Monitoring & Alerting Agent. Your objective is to export system performance metrics, track the health of all agents, and dispatch real-time alerts to operators."
*   **Execution Rules:**
    1.  **Metric Export:** Export Prometheus metrics including agent loop latencies, database write status, API rate limit usage, slippage, and portfolio balances.
    2.  **Heartbeat Auditing:** Audit the Redis heartbeat keys. If any agent heartbeat is missing for $> 30$ seconds, send a panic event to the Orchestrator.
    3.  **Emergency Dispatch:** Upon receiving a system HALT signal, trigger immediate broadcasts via Telegram API and SMS gateways to registered operators with complete error payloads and traceback links.

### 2.10. Orchestrator Agent
*   **Prompt Instruction:**
    "You are the Orchestrator. You manage the execution graph and coordinate state snapshots, error handling, and message passing between agents."
*   **Execution Rules:**
    1.  **Tick Trigger:** Initiate execution loop sequentially on a cron tick (or WebSocket update).
    2.  **State Persistence:** Save a serialized JSON snapshot of all agent states, balances, and parameters to TimescaleDB at the end of each tick.
    3.  **Circuit Breaker Recovery:**
        *   Soft trigger reset: Auto-resume operations if the trigger condition (e.g., API errors, high spread) has cleared for $\ge 30$ continuous minutes.
        *   Hard trigger reset: If a kill switch triggers twice within 24 hours, freeze the system and require manual command line input to resume.
    4.  **Bootstrapping Control:** Manage initial system activation phases:
        *   *Phase B1 (Seed):* Deploy 10% of planned USD capital to establish trading floor and initiate seed grid.
        *   *Phase B2 (DCA Ramp):* Deploy 5% of remaining reserve weekly to accumulate core BTC until core BTC reaches target (60-80%).
        *   *Phase B3 (Opportunistic):* Full system activation with adaptive multipliers and volatility harvesting.

---

## 3. Configuration Parameters

The following parameters must be configured in `config/production.json` and are enforced as system-wide bounds by the agents:

| Parameter | Default Value | Enforcing Agent | Description |
|---|---|---|---|
| `reserve_floor` | 10% — 20% | Risk Agent | Minimum USDT reserve value as % of total portfolio value. |
| `daily_deployment_cap` | 5% — 10% | Risk Agent | Maximum percentage of portfolio deployed to new buy orders in any 24h. |
| `hot_exchange_cap` | 25% | Risk Agent | Maximum exchange-held BTC as % of total portfolio value. |
| `min_profit_threshold` | ~0.375% | Grid, Risk Agents | Gated profit threshold (equal to 1.5x round-trip trading cost). |
| `core_btc_target` | 60% — 80% | Inventory Agent | Long-term target allocation for Core BTC. |
| `trading_target` | 10% — 25% | Inventory Agent | Swing inventory target allocation. |
| `trading_floor` | 5% | Grid Agent | Minimum trading sleeve balance before buy/sell sizing limits kick in. |
| `promotion_threshold` | 1.3× trading_target | Inventory Agent | Multiplier over trading target that triggers core transfer if held for 7 days. |

---

## 4. Error Handling & Recovery

All agents must adhere to the following error handling policies during execution loops:

1.  **Transient API Errors:** On exchange rate-limiting (HTTP 429) or transient timeouts, the Execution Agent must retry with exponential backoff:
    $$T_{\text{wait}} = 2^{\text{attempt}} \times 500\text{ms} + \text{jitter}$$
    Maximum retry limit is set to 5 attempts before raising a fatal exception.
2.  **Rate Limiting & Cooldown:** If rate limit warnings are received, throttle execution interval by doubling the Orchestrator's tick time for a 15-minute cooldown.
3.  **Partial Loop Failure Recovery:** If any agent in the serialization sequence fails (e.g. Regime Agent crashes mid-tick), the Orchestrator must roll back any proposed state transitions and trigger an emergency soft halt.
4.  **State Recovery:** On startup or crash recovery, the Inventory Agent must reconstruct current balances and cost basis by querying the database TimescaleDB ledger snapshot and validating against the exchange REST API balance state.

---

## 5. Inter-Agent Communication Protocol

Agents communicate asynchronously via a Redis Pub/Sub backplane using the following standards:

1.  **Payload Schema:** All messages must be formatted as structured JSON with the following envelope:
    ```json
    {
      "message_id": "uuid4",
      "timestamp": "ISO-8601-UTC",
      "tick_id": 12345,
      "sender": "agent_name",
      "recipient": "agent_name",
      "payload": {},
      "signature": "hmac_sha256_hash"
    }
    ```
2.  **Channel Structure:** Redis Pub/Sub channels are organized by message category:
    *   `broadcast:market_data` (Data → Feature → Regime)
    *   `orchestration:ticks` (Orchestrator commands)
    *   `execution:orders` (Grid → Risk → Execution)
    *   `execution:fills` (Execution → Portfolio → Inventory)
3.  **Priority Levels:** Messages must include a priority header:
    *   `HIGH`: Emergency halts, risk violations, order cancellation commands.
    *   `MEDIUM`: Tick orchestration, proposed orders, fills.
    *   `LOW`: Heartbeats, non-critical telemetry, metrics export.
