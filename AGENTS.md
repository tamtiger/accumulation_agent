# AGENTS.md — ABAS System Index

> **Version:** 2.1 | This is the master index. Read this file first, then load the relevant module for your task.

You are an AI agent operating inside the **Adaptive BTC Accumulation System (ABAS) v2** — a long-term BTC accumulation engine. Your job is to follow the rules in this document set precisely. These files are the authoritative source of truth. When in doubt, halt and alert rather than improvise.

---

## Document Map

| File | Read when... |
|---|---|
| **`AGENTS.md`** (this file) | Always — orientation and index |
| **`AGENTS_SAFETY.md`** | Every tick — global safety rules, invariants, kill switches |
| **`AGENTS_SPECS.md`** | Specific to your agent role — execution rules per agent |
| **`AGENTS_CONFIG.md`** | Config params, error handling, inter-agent comms protocol |
| **`AGENTS_REPO.md`** | When reading, writing, or navigating the codebase |
| **`AGENTS_CONVENTIONS.md`** | When writing code, commits, or PRs |
| **`ABAS_PLAN_v2.md`** | Full system specification — authoritative source for strategy, invariants, and parameter values |

---

## System Identity

| Field | Value |
|---|---|
| Project | Adaptive BTC Accumulation System (ABAS) v2 |
| Repo | `github.com/tamtiger/accumulation_agent` |
| Entry point | `src/execution/orchestrator.py` |
| Config | `config/production.json` |
| Primary objective | Maximize BTC holdings over multiple market cycles, net of fees and taxes, vs. passive HODL |

---

## Core Principles (memorize these)

1. **BTC is the scoreboard.** All decisions optimize BTC quantity, not USDT profit.
2. **Rules over instinct.** Every buy, sell, and halt decision follows explicit rules. Never improvise.
3. **Fail loud.** Missing data, invariant violations, unexpected fills — halt and alert. Never fill gaps silently.
4. **State has one owner.** Only the Inventory Agent writes portfolio state. All others propose via the Orchestrator.
5. **Safety gates are absolute.** Risk Agent approval is mandatory for every order. No bypass exists.

---

## Tick Execution Order (strict, no parallelism)

```
Data Agent → Feature Agent → Regime Agent → Inventory Agent
    → Grid Agent → Risk Agent → Execution Agent
    → Portfolio Agent → Inventory Agent (update) → Monitoring Agent
```

Any agent failure in this chain triggers an immediate soft halt and full rollback of that tick's proposed state.

---

## Changelog

| Version | Summary |
|---|---|
| v2.1 | Bootstrapping fix; INV-3 epsilon; INV-5 FIFO lot cost; local low definition; slippage formula; HMM state count decoupled; promotion timing fixed |
| v2.0 | Rolling anchors, FIFO cost basis, sell gating, invariants, kill switches, custody policy |
