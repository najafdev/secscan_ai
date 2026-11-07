# DeepSeek Multi-Key Failover — Design

- **Date:** 2026-06-21
- **Status:** Approved (pending spec review)
- **Scope:** DeepSeek provider only

## Summary

Let users store a **pool of DeepSeek API keys** so that when the active key
goes **bad** (revoked/invalid) or **runs out** (insufficient balance / quota),
HackBot automatically rotates to the next working key and **retries the same
request transparently**, with a brief notice. Keys are managed from the REPL
(`/key add`, `/keys`, `/key remove`). All other providers behave exactly as
they do today.

## Motivation

A single DeepSeek key is a single point of failure: when it is revoked or its
balance hits zero, every request fails until the user notices and manually
swaps the key. A small key pool with automatic failover keeps an assessment or
chat session running without interruption.

## Goals

- Store multiple DeepSeek keys, ordered by priority.
- On a rotation-worthy failure, switch to the next untried key and retry the
  same request with no user action.
- Manage the pool interactively: add, list, remove.
- Full backward compatibility with existing single-key configs.

## Non-goals (out of scope)

- Cross-provider failover (DeepSeek → Groq, etc.).
- Multi-key support for any provider other than DeepSeek.
- Rotating on transient errors (plain rate-limits, network/timeout, model-not-found).
- A GUI management surface for the pool (failover still works in the GUI because
  it is engine-level; only the *management UI* is deferred — see Future Work).
- Encrypted key storage (keys remain plaintext in `config.yaml`, unchanged from
  today's `api_key`).
- Changing the `hackbot setup` command (it stays single-key and seeds the pool).

## Requirements (decisions captured during brainstorming)

1. **Failover scope:** more keys for the **same provider** (DeepSeek), not other providers.
2. **Trigger behavior:** **automatic** rotation **with retry** of the failed request.
3. **What counts as failure worth rotating:** key is **dead** (`401`/`403`) or
   **out of credit** (`402` Insufficient Balance, or `429` with
   `insufficient_quota`). Plain `429` rate-limits, `404`, `400`, and
   network/timeout errors do **not** rotate.
4. **Storage:** a single DeepSeek key pool (DeepSeek-only feature; no per-provider map).
5. **Management:** REPL commands `/key add <key>`, `/keys`, `/key remove <n>`.
6. **Bad-key memory:** session-only. Every run starts fresh with the full pool
   (quotas refill, balances get topped up).

## Design

### 1. Data model & config (`config.py`)

- Add **`api_keys: list[str]`** to `AIConfig` (default `[]`): the ordered pool,
  highest priority first. Update `DEFAULT_CONFIG["ai"]` and `save_config()` to
  round-trip it.
- **Invariant:** `api_key` always mirrors the **active** key (`pool[0]` at
  startup). Every existing reader of `config.ai.api_key` keeps working
  unchanged — this is what preserves backward compatibility.
- **Reconciliation** at the end of `load_config()`, after env-var overrides so
  env-provided keys still win:

  ```python
  keys = [k for k in dict.fromkeys([api_key] + api_keys) if k]  # dedupe, active-first
  merged["ai"]["api_keys"] = keys
  merged["ai"]["api_key"]  = keys[0] if keys else ""
  ```

  Effects: an old single-key config auto-seeds the pool `[that key]`; a pool
  config sets the active key to `pool[0]`; an env-provided key is prepended as
  the active key. No migration script required.
- **Pure pool helpers** (testable without the CLI), operating on `AIConfig` and
  maintaining the dedupe + active-first invariant:
  - `add_key(cfg, key) -> None`
  - `remove_key(cfg, index) -> str` (returns removed key; raises on bad index)
  - `set_active_key(cfg, key) -> None` (moves/inserts key to front, updates `api_key`)

### 2. Engine failover (`core/engine.py`)

- **Gating:** failover engages only when `config.provider == "deepseek"`. Any
  other provider performs a single attempt and raises on error — today's
  behavior, unchanged.
- **Shared error classifier:** extract the categorization currently inside
  `validate_api_key()` into `_key_failure_reason(exc) -> str | None`, used by
  both validation and failover so they cannot drift:

  | Condition | Result |
  |---|---|
  | `status_code == 401` | `"dead"` → rotate |
  | `status_code == 403` | `"disabled"` → rotate |
  | `status_code == 402` (Insufficient Balance) | `"out of credit"` → rotate |
  | `429` with `insufficient_quota` / `insufficient balance` in message | `"out of credit"` → rotate |
  | plain `429` rate-limit, `404`, `400`, timeout/connection | `None` → do not rotate, re-raise |

  Classification reads `getattr(exc, "status_code", None)` and falls back to
  scanning `str(exc)` for the quota markers.
- **Engine runtime state:** `self._bad: dict[str, str]` (key → reason) tracks
  session-bad keys; the active key is `config.api_key`. A `refresh_pool()` method
  re-reads the config after the pool is mutated by a command.
- **`_with_failover(do_call, *, on_notice)`** wraps the completion call:
  1. Try `do_call(self.client)`.
  2. On exception, compute `reason = _key_failure_reason(exc)`. If `reason is
     None` or failover is not enabled → re-raise.
  3. Mark the active key bad (`self._bad`), pick the next key not in `self._bad`,
     set `config.api_key` to it, rebuild via `_setup_client()`.
  4. If no good key remains → raise `KeyPoolExhaustedError` with a masked
     per-key summary (`sk-…a1b2: out of credit`) and an "add one with `/key add`"
     hint.
  5. Otherwise fire `on_notice(...)` and retry.
- **`_blocking_chat`** runs inside `_with_failover` directly (the call is atomic).
- **Streaming boundary (`_stream_chat`):** auto-retry only if the failure happens
  **before the first token** is emitted (exactly when auth/quota errors fire). If
  any token already streamed, re-raise rather than duplicating output:

  ```python
  emitted = False
  try:
      stream = self.client.chat.completions.create(..., stream=True)
      for chunk in stream:
          tok = ...
          if tok:
              emitted = True
              on_token(tok)
  except Exception as e:
      if emitted or _key_failure_reason(e) is None or not failover_enabled:
          raise
      # rotate to next key (or raise KeyPoolExhaustedError) and retry from the top
  ```

- **Notice plumbing (UI-agnostic):** `AIEngine` gains an
  `on_notice: Callable[[str], None] | None` attribute (no signature change to
  modes). The CLI sets it once to `print_warning` via a `_wire_engine()` helper,
  re-applied wherever the engine is rebuilt (`/key`, `/model`, `/provider`). The
  GUI may set its own sink. Message form:
  `DeepSeek key #1 out of credit — switched to key #2`.
- **`KeyPoolExhaustedError`** is a `RuntimeError` subclass so existing CLI/agent
  error handling surfaces it normally, while tests can assert on its type.

### 3. REPL key-management commands (`cli.py`)

CLI handlers are thin wrappers over the `config.py` pool helpers; after any
mutation they call `save_config()` and re-wire the engine.

- **`/key <key>`** — unchanged entry point. Sets the active key; for DeepSeek the
  key is moved/inserted to the front of the pool. A real key is `sk-…`, so it
  never collides with the subcommand words below. Routing lives in `_set_key`:
  if the first token is `add` / `remove` / `list`, dispatch to the pool handler;
  otherwise treat the whole argument as a key (today's behavior).
- **`/key add <key>`** — validate via `validate_api_key`, then append to the pool
  (dedup). Warn-but-add on failed validation (consistent with today's `_set_key`,
  which saves even when validation fails).
- **`/key remove <n>`** — remove pool entry `#n` (1-indexed). If it was active,
  the new active becomes `pool[0]` and the client rebuilds. Out-of-range or
  non-numeric → usage error.
- **`/keys`** — new entry in the command dispatch table; lists the pool masked
  (`sk-…a1b2`), marking the active key (`●`) and any session-bad keys
  (`✗ <reason>`), plus the count. `/key list` aliases to it.
- **Scope guard:** pool commands are DeepSeek-only. On another provider,
  `/key add` prints `Multi-key pooling is DeepSeek-only — switch with /provider
  deepseek`; `/keys` notes the same and shows the single active key. `/key
  <key>` works on every provider.

### 4. Error handling & edge cases

- **All keys exhausted mid-session** → `KeyPoolExhaustedError` propagates through
  `_handle_message` / the agent loop, printing the masked summary + `/key add` hint.
- **Removing the last key** → empty pool → falls back to today's
  "API key not configured" messaging.
- **Duplicate add** → no-op with a note.
- **Adding an invalid key** → warn but still add (mirrors current behavior so a
  transient validation failure does not block the user).
- **Non-DeepSeek provider** → pool is ignored by the engine; single-attempt
  behavior, byte-for-byte unchanged.
- The rotation notice prints before the response streams (failover happens before
  the first token), so it never interleaves with streamed output.

## Testing

- **`tests/test_engine.py`**
  - `_key_failure_reason` table: `401`/`403`/`402`/`429+insufficient_quota` →
    rotate reasons; plain `429`, `404`, connection → `None`.
  - Failover rotates: mocked client raises `402` on key 1, succeeds on key 2 →
    asserts retry happened, notice fired, key 2's content returned.
  - All-exhausted → `KeyPoolExhaustedError` with masked summary.
  - **Non-DeepSeek provider:** `402` raises immediately, no rotation.
  - Streaming: failure before first token rotates and retries; failure after a
    token re-raises (no duplicate output).
  - All via a mocked OpenAI client — no network calls.
- **`tests/test_config.py`**
  - Reconciliation: single key → pool seeded; pool → `api_key == pool[0]`;
    dedupe + active-first; env key prepended.
  - `api_keys` save/load round-trip.
  - `add_key` / `remove_key` / `set_active_key` helpers (including invariant and
    bad-index handling).

## Backward compatibility

- Existing `config.yaml` files with a single `ai.api_key` load unchanged and are
  silently upgraded to a one-entry pool on first load.
- `config.ai.api_key` keeps its meaning (the active key) for every existing reader.
- `/key <key>`, `hackbot setup`, and all provider env vars keep working as before.

## Future work (explicitly deferred)

- GUI management UI for the pool (`/api/config` could accept `api_keys`).
- Optional comma-separated bulk entry (`DEEPSEEK_API_KEY=k1,k2,k3`, `setup`).
- Generalizing the pool to other providers, if ever wanted.
