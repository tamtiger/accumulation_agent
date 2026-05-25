# AGENTS_CONVENTIONS.md — Coding Conventions & Workflow Rules

> Load this file when writing code, commits, or PRs.

---

## 1. General Conventions

- **Python 3.11+** only. Use `match/case`, `tomllib`, `ExceptionGroup` where appropriate.
- **Formatter:** `ruff format`. Line length: 100.
- **Linter:** `ruff check` with rules `E, F, I, N, UP, B, SIM`. No bare `except:`.
- **Type hints:** Required on all public functions and class methods. Add `from __future__ import annotations` at the top of every file.
- **Imports:** stdlib → third-party → internal, separated by blank lines. Absolute imports only.
- **No `print()` in production code.** Use structured logging.

---

## 2. Naming Conventions

| Entity | Style | Example |
|---|---|---|
| Modules | `snake_case` | `fifo_ledger.py` |
| Classes | `PascalCase` | `InventoryAgent` |
| Functions / methods | `snake_case` | `compute_avg_cost()` |
| Constants | `UPPER_SNAKE_CASE` | `INV3_EPSILON = 1e-8` |
| Config keys | `snake_case` | `reserve_floor` |
| Redis keys | `namespace:key` | `heartbeat:inventory_agent` |
| DB table names | `snake_case` | `fifo_lots`, `order_fills` |

---

## 3. Structured Logging

Use `structlog`. Every log entry must include `agent`, `tick_id`, `action`.

```python
import structlog
log = structlog.get_logger()

log.info(
    "order_proposed",
    agent="grid_agent",
    tick_id=tick_id,
    action="buy",
    qty_btc=0.015,
    price_usdt=62_400.0,
    regime="sideways",
)
```

**Never log:** API keys, secrets, credentials, cold wallet addresses.

---

## 4. Error Handling

```python
# Correct — specific exception, log, re-raise or halt
try:
    result = await exchange.fetch_order(order_id)
except ccxt.NetworkError as exc:
    log.error("exchange_network_error", agent="execution_agent", order_id=order_id, error=str(exc))
    raise

# Wrong — swallows error silently
try:
    result = await exchange.fetch_order(order_id)
except Exception:
    pass
```

- Never catch `BaseException` or bare `Exception` without re-raising or triggering a halt.
- All exchange calls use retry logic (see `AGENTS_CONFIG.md` §2 — Transient API Errors).
- Invariant violations raise `InvariantViolationError` → Orchestrator converts to HALT.

---

## 5. Async & I/O

- All I/O-bound agent loops are `async`. Use `asyncio`; no `threading`.
- Never use `asyncio.sleep(0)` — use explicit durations.
- DB calls: `asyncpg`. Redis calls: `aioredis`.

---

## 6. Financial Arithmetic

**Never use `float` for monetary or quantity values.** Use `decimal.Decimal` with explicit precision.

```python
from decimal import Decimal, ROUND_DOWN

qty = Decimal("0.123456789").quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
```

Rounding for exchange submission always uses `ROUND_DOWN` to avoid over-ordering.

---

## 7. Configuration

- All tunable values live in `config/production.json`. No magic numbers in code.
- Load config via a typed `Settings` dataclass at startup. Never scatter `json.load()` across modules.
- Environment overrides: `config/paper.json`, `config/test.json`.

---

## 8. Testing

- **Unit tests:** `pytest` + `pytest-asyncio`. Every public function has at least one test.
- **Property tests:** `hypothesis`. All invariant-touching code has a property test.
- **Exchange mocks:** `pytest-mock`. Never hit live exchange in tests.
- **File mirroring:** `src/inventory/fifo_ledger.py` → `tests/unit/inventory/test_fifo_ledger.py`

---

## 9. Branch Strategy

```
main            # production only; protected; PR + review required
├── develop     # integration branch; all features merge here first
└── feature/*   # one branch per feature or fix
    hotfix/*    # emergency production patches only
```

Never commit directly to `main` or `develop`.
Branch naming: `feature/fifo-sell-gating`, `fix/inv3-epsilon`, `hotfix/halt-loop`

---

## 10. Commit Messages

Follow Conventional Commits: `<type>(<scope>): <short description>`

| Type | When |
|---|---|
| `feat` | New capability |
| `fix` | Bug fix |
| `refactor` | Code change, no behavior change |
| `test` | Adding or fixing tests |
| `docs` | Documentation only |
| `chore` | Tooling, deps, CI |
| `halt` | Emergency production stop — use sparingly |

Examples:
```
feat(inventory): add per-lot FIFO export for tax reporting
fix(risk): replace INV-3 strict equality with epsilon tolerance
test(property): add hypothesis test for sell gating under all regimes
```

---

## 11. Pull Request Rules

- Every PR targets `develop`, not `main`.
- PR description must include: what changed, which agents are affected, test evidence.
- Required checks before merge:
  - `ruff check` + `ruff format --check` pass
  - All unit + property tests pass
  - No new `# type: ignore` without an explanation comment
  - `pytest tests/property/test_invariants.py` passes explicitly
- PRs touching `src/risk/invariants.py` or `src/inventory/fifo_ledger.py` require a review comment explicitly acknowledging financial impact.

---

## 12. Release to Production

1. Merge `develop` → `main` via PR (no squash — preserve history)
2. Tag: `vMAJOR.MINOR.PATCH`
3. Deploy via Docker Compose
4. Run paper trading smoke test ≥ 24h before enabling live orders
5. Monitor kill switch dashboard for first 48h post-deploy

---

## 13. Secrets Management

- **Never commit secrets.** All `.env` files are gitignored.
- Rotate API keys immediately if accidentally exposed.
- All secrets loaded from Vault / KMS at runtime via `src/api/secrets.py`.
- Local dev: `.env.local` (gitignored). CI: environment variables from pipeline.

---

## 14. Dependencies

- Add via `pip install <pkg>` + `pip freeze > requirements.txt`, or `uv add`.
- Justify every new dependency in the PR description. Prefer stdlib over third-party for simple tasks.
- Pin all dependencies to exact versions in `requirements.txt`.
