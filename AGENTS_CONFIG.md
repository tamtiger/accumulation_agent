# AGENTS_CONFIG.md — Configuration, Error Handling & Comms Protocol

> Load this file when looking up parameter values, handling errors, or implementing inter-agent messaging.

---

## 1. Configuration Parameters

All values configured in `config/production.json`. Loaded once at startup — immutable for the duration of a run.

| Parameter | Default | Enforcing Agent | Description |
|---|---|---|---|
| `reserve_floor` | 10–20% | Risk Agent | Min USDT reserve as % of total portfolio value |
| `daily_deployment_cap` | 5–10% | Risk Agent | Max % of portfolio deployed in new buy orders per 24h |
| `hot_exchange_cap` | 25% | Risk Agent | Max exchange-held BTC as % of total portfolio value |
| `min_profit_threshold` | ~0.375% | Grid, Risk | Min sell profit = 1.5× round-trip cost. Applied to FIFO lot cost. |
| `core_btc_target` | 60–80% | Inventory | Long-term target allocation for Core BTC |
| `trading_target` | 10–25% | Inventory | Swing inventory target allocation |
| `trading_floor` | 5% of total_portfolio | Grid | Min trading sleeve before sell sizing is blocked. Expressed as % of total portfolio value. |
| `promotion_threshold` | 1.3× trading_target | Inventory | Trigger for core transfer if held 7 consecutive daily snapshots |
| `inv3_epsilon` | 1e-8 BTC | Risk | Tolerance for INV-3 balance conservation check |

---

## 2. Error Handling & Recovery

### Transient API Errors

On HTTP 429 or timeout, retry with exponential backoff + jitter:
```
T_wait = 2^attempt × 500ms + jitter
```
Maximum 5 attempts before raising fatal exception.

### Rate Limiting

On rate limit warnings → double Orchestrator tick interval for 15-minute cooldown.

### Partial Loop Failure

If any agent in the tick chain fails mid-tick → Orchestrator rolls back all proposed state transitions for that tick → triggers emergency soft halt.

### Startup / Crash Recovery

Inventory Agent reconstructs state by:
1. Querying latest TimescaleDB `portfolio_snapshots` entry
2. Replaying all `order_fills` since that snapshot
3. Validating reconstructed balances against exchange REST API

Do not proceed if reconstructed state diverges from exchange balance by > `inv3_epsilon`.

---

## 3. Inter-Agent Communication Protocol

All messages via Redis Pub/Sub.

### Message Envelope

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

### Channel Structure

| Channel | Direction |
|---|---|
| `broadcast:market_data` | Data Agent → Feature Agent → Regime Agent |
| `orchestration:ticks` | Orchestrator → all agents |
| `execution:orders` | Grid Agent → Risk Agent → Execution Agent |
| `execution:fills` | Execution Agent → Portfolio Agent → Inventory Agent |
| `monitoring:heartbeat` | All agents → Monitoring Agent (every 10s) |
| `monitoring:halt` | Risk Agent / Orchestrator → Monitoring Agent (emergency broadcast) |

### Priority Levels

| Priority | Used for |
|---|---|
| `HIGH` | Emergency halts, risk violations, order cancellations |
| `MEDIUM` | Tick orchestration, proposed orders, fills |
| `LOW` | Heartbeats, telemetry, metrics export |
