# DeepSeek Multi-Key Failover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users store a pool of DeepSeek API keys so HackBot automatically rotates to the next working key and retries the request when the active key is dead or out of credit.

**Architecture:** A key pool (`AIConfig.api_keys`) persists in `config.yaml` with the active key mirrored into the existing `api_key` field for backward compatibility. `AIEngine` classifies failures and, only for the `deepseek` provider, rotates to the next untried key and retries — transparently for blocking calls, and (for streaming) only when no token has been emitted yet. REPL commands manage the pool.

**Tech Stack:** Python 3.9+, OpenAI SDK (provider-agnostic client), Click + Rich CLI, pytest with `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-06-21-deepseek-multi-key-failover-design.md`

---

## File Structure

- `hackbot/config.py` — add `api_keys` field, `reconcile_keys()`, pool helpers (`add_key`/`remove_key`/`set_active_key`), `mask_key()`. Persist via `save_config`.
- `hackbot/core/engine.py` — `KeyPoolExhaustedError`, `_key_failure_reason()` classifier, rotation state + `_maybe_rotate()`, failover loops in `_blocking_chat`/`_stream_chat`, `on_notice` hook.
- `hackbot/cli.py` — `_rebuild_engine()` helper, `_set_key()` subcommand routing, `_key_add`/`_key_remove`/`_list_keys`, `/keys` dispatch entry.
- `hackbot/ui/__init__.py` — `/help` text additions.
- `tests/test_config.py`, `tests/test_engine.py`, `tests/test_keypool_cli.py` — coverage.

---

## Task 1: Config — `api_keys` field, persistence & reconciliation

**Files:**
- Modify: `hackbot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (extend the import from `hackbot.config` to include `reconcile_keys`, `save_config`):

```python
from hackbot.config import reconcile_keys, save_config


def test_reconcile_seeds_pool_from_single_key():
    ai = {"api_key": "sk-a", "api_keys": []}
    reconcile_keys(ai)
    assert ai["api_keys"] == ["sk-a"]
    assert ai["api_key"] == "sk-a"


def test_reconcile_active_is_pool_first():
    ai = {"api_key": "", "api_keys": ["sk-a", "sk-b"]}
    reconcile_keys(ai)
    assert ai["api_key"] == "sk-a"


def test_reconcile_env_key_prepended_and_deduped():
    ai = {"api_key": "sk-env", "api_keys": ["sk-a", "sk-env", "sk-b"]}
    reconcile_keys(ai)
    assert ai["api_keys"] == ["sk-env", "sk-a", "sk-b"]
    assert ai["api_key"] == "sk-env"


def test_reconcile_empty_pool():
    ai = {"api_key": "", "api_keys": []}
    reconcile_keys(ai)
    assert ai["api_keys"] == []
    assert ai["api_key"] == ""


def test_api_keys_round_trip(tmp_path, monkeypatch):
    import hackbot.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", tmp_path / "config.yaml")
    for var in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "HACKBOT_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    cfg = cfgmod.HackBotConfig()
    cfg.ai.provider = "deepseek"
    cfg.ai.api_keys = ["sk-a", "sk-b"]
    cfg.ai.api_key = "sk-a"
    cfgmod.save_config(cfg)

    loaded = cfgmod.load_config()
    assert loaded.ai.api_keys == ["sk-a", "sk-b"]
    assert loaded.ai.api_key == "sk-a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -k "reconcile or round_trip" -v`
Expected: FAIL — `ImportError: cannot import name 'reconcile_keys'` (and `AIConfig` has no `api_keys`).

- [ ] **Step 3: Implement**

In `hackbot/config.py`:

3a. Add `api_keys` to the default config — inside `DEFAULT_CONFIG["ai"]`, after `"base_url": "",`:

```python
        "api_keys": [],
```

3b. Add the field to `AIConfig` (after `api_key: str = ""`):

```python
    api_keys: List[str] = field(default_factory=list)
```

3c. Persist it — in `save_config`, inside the `"ai": { ... }` dict, after `"api_key": cfg.ai.api_key,`:

```python
            "api_keys": cfg.ai.api_keys,
```

3d. Add the reconciliation function (place it just above `load_config`):

```python
def reconcile_keys(ai: Dict[str, Any]) -> None:
    """Normalize the API key pool in an ``ai`` config dict, in place.

    Dedupes, drops empties, and keeps the active key first so the invariant
    ``api_key == api_keys[0]`` always holds. Seeds the pool from a legacy
    single ``api_key`` and lets an env-provided ``api_key`` take priority by
    placing it first.
    """
    pool = [k for k in dict.fromkeys([ai.get("api_key", "")] + list(ai.get("api_keys") or [])) if k]
    ai["api_keys"] = pool
    ai["api_key"] = pool[0] if pool else ""
```

3e. Call it in `load_config`, immediately after the `allowed_tools` migration block and before `cfg = HackBotConfig(`:

```python
    reconcile_keys(merged.setdefault("ai", {}))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (all existing config tests plus the 5 new ones).

- [ ] **Step 5: Commit**

```bash
git add hackbot/config.py tests/test_config.py
git commit -m "$(printf 'feat(config): add DeepSeek api_keys pool with reconciliation\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 2: Config — pool helpers & key masking

**Files:**
- Modify: `hackbot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (extend the `hackbot.config` import to include `add_key`, `remove_key`, `set_active_key`, `mask_key`):

```python
from hackbot.config import add_key, remove_key, set_active_key, mask_key


def test_add_key_appends_and_dedupes():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a"])
    add_key(cfg, "sk-b")
    assert cfg.api_keys == ["sk-a", "sk-b"]
    add_key(cfg, "sk-b")  # duplicate is a no-op
    assert cfg.api_keys == ["sk-a", "sk-b"]
    assert cfg.api_key == "sk-a"  # active unchanged


def test_add_key_seeds_active_when_empty():
    cfg = AIConfig(provider="deepseek", api_key="", api_keys=[])
    add_key(cfg, "sk-a")
    assert cfg.api_keys == ["sk-a"]
    assert cfg.api_key == "sk-a"


def test_remove_active_key_promotes_next():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    removed = remove_key(cfg, 0)
    assert removed == "sk-a"
    assert cfg.api_keys == ["sk-b"]
    assert cfg.api_key == "sk-b"


def test_remove_nonactive_key_keeps_active():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    removed = remove_key(cfg, 1)
    assert removed == "sk-b"
    assert cfg.api_keys == ["sk-a"]
    assert cfg.api_key == "sk-a"


def test_remove_key_bad_index_raises():
    cfg = AIConfig(api_keys=["sk-a"])
    with pytest.raises(IndexError):
        remove_key(cfg, 5)


def test_set_active_key_moves_to_front():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    set_active_key(cfg, "sk-b")
    assert cfg.api_keys == ["sk-b", "sk-a"]
    assert cfg.api_key == "sk-b"


def test_set_active_key_new_key_inserts_front():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a"])
    set_active_key(cfg, "sk-new")
    assert cfg.api_keys == ["sk-new", "sk-a"]
    assert cfg.api_key == "sk-new"


def test_mask_key():
    assert mask_key("sk-1234567890abcd") == "sk-12…abcd"
    assert mask_key("short") == "sho…"
    assert mask_key("") == "(empty)"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -k "add_key or remove or set_active or mask" -v`
Expected: FAIL — `ImportError: cannot import name 'add_key'`.

- [ ] **Step 3: Implement**

Add to `hackbot/config.py` (just below `reconcile_keys`):

```python
def add_key(cfg: "AIConfig", key: str) -> None:
    """Append *key* to the pool if not already present; keep ``api_key`` valid."""
    key = key.strip()
    if not key or key in cfg.api_keys:
        return
    cfg.api_keys.append(key)
    if not cfg.api_key:
        cfg.api_key = cfg.api_keys[0]


def remove_key(cfg: "AIConfig", index: int) -> str:
    """Remove and return the pool entry at *index*. Raises IndexError if invalid.

    If the removed key was the active one, the new active key becomes the new
    ``api_keys[0]`` (or empty when the pool is exhausted).
    """
    removed = cfg.api_keys.pop(index)  # raises IndexError on bad index
    cfg.api_key = cfg.api_keys[0] if cfg.api_keys else ""
    return removed


def set_active_key(cfg: "AIConfig", key: str) -> None:
    """Make *key* the active key by moving/inserting it at the front of the pool."""
    key = key.strip()
    if not key:
        return
    if key in cfg.api_keys:
        cfg.api_keys.remove(key)
    cfg.api_keys.insert(0, key)
    cfg.api_key = key


def mask_key(key: str) -> str:
    """Return a display-safe masked form of an API key."""
    if not key:
        return "(empty)"
    if len(key) <= 8:
        return key[:3] + "…"
    return f"{key[:5]}…{key[-4:]}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add hackbot/config.py tests/test_config.py
git commit -m "$(printf 'feat(config): add pool helpers and mask_key\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 3: Engine — failure classifier & `KeyPoolExhaustedError`

**Files:**
- Modify: `hackbot/core/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_engine.py` (extend the `hackbot.core.engine` import to include `KeyPoolExhaustedError`):

```python
from hackbot.core.engine import KeyPoolExhaustedError


class TestKeyFailureReason:
    """AIEngine._key_failure_reason classifies which failures rotate a key."""

    @pytest.mark.parametrize("message,expected", [
        ("Error code: 401 - Unauthorized", "dead"),
        ("Invalid API key provided", "dead"),
        ("Error code: 403 Forbidden", "disabled"),
        ("Error code: 402 - Insufficient Balance", "out of credit"),
        ("Error code: 429 - You exceeded your current quota, insufficient_quota", "out of credit"),
        ("Error code: 429 - Rate limit exceeded", None),
        ("Error code: 404 - Model not found", None),
        ("Error code: 400 - Bad request", None),
        ("Connection refused", None),
        ("Request timed out", None),
    ])
    def test_classifier(self, message, expected):
        assert AIEngine._key_failure_reason(Exception(message)) == expected

    def test_classifier_uses_status_code(self):
        exc = Exception("payment required")
        exc.status_code = 402
        assert AIEngine._key_failure_reason(exc) == "out of credit"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -k "KeyFailureReason" -v`
Expected: FAIL — `ImportError: cannot import name 'KeyPoolExhaustedError'`.

- [ ] **Step 3: Implement**

In `hackbot/core/engine.py`:

3a. Change the config import line `from hackbot.config import AIConfig` to:

```python
from hackbot.config import AIConfig, mask_key
```

3b. Add the exception class immediately after the imports (above `# ── Provider Registry`):

```python
class KeyPoolExhaustedError(RuntimeError):
    """Raised when every key in the DeepSeek pool is dead or out of credit."""
```

3c. Add the classifier as a `@staticmethod` on `AIEngine` (place it just above `validate_api_key`):

```python
    @staticmethod
    def _key_failure_reason(exc: Exception) -> Optional[str]:
        """Classify an API error as a key-rotation reason, or None.

        Returns 'out of credit' | 'dead' | 'disabled' when the *current key* is
        unusable, or None for transient / non-key errors (plain rate-limits,
        404 model-not-found, 400, timeouts, connection failures) that rotating
        through the pool would not fix.
        """
        msg = str(exc).lower()
        code = getattr(exc, "status_code", None)
        if (code == 402 or "insufficient balance" in msg or "insufficient_quota" in msg
                or "exceeded your current quota" in msg):
            return "out of credit"
        if (code == 401 or "401" in msg or "unauthorized" in msg
                or "invalid api key" in msg or "invalid_api_key" in msg):
            return "dead"
        if code == 403 or "403" in msg or "forbidden" in msg:
            return "disabled"
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -k "KeyFailureReason" -v`
Expected: PASS (12 parametrized cases + status-code case).

- [ ] **Step 5: Commit**

```bash
git add hackbot/core/engine.py tests/test_engine.py
git commit -m "$(printf 'feat(engine): add key-failure classifier and KeyPoolExhaustedError\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 4: Engine — blocking-call failover

**Files:**
- Modify: `hackbot/core/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_engine.py`:

```python
class TestBlockingFailover:
    @patch("hackbot.core.engine.OpenAI")
    def test_rotates_on_out_of_credit(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        ok = MagicMock()
        ok.choices = [MagicMock()]
        ok.choices[0].message.content = "hi from key2"
        mock_client.chat.completions.create.side_effect = [
            Exception("Error code: 402 - Insufficient Balance"),
            ok,
        ]
        cfg = AIConfig(provider="deepseek", model="deepseek-chat",
                       api_key="sk-1", api_keys=["sk-1", "sk-2"])
        engine = AIEngine(cfg)
        notices = []
        engine.on_notice = notices.append

        result = engine.chat(create_conversation("chat"), stream=False)

        assert result == "hi from key2"
        assert cfg.api_key == "sk-2"
        assert mock_client.chat.completions.create.call_count == 2
        assert notices and "switched to key #2" in notices[0]

    @patch("hackbot.core.engine.OpenAI")
    def test_raises_when_all_keys_exhausted(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            Exception("Error code: 402 - Insufficient Balance"),
            Exception("Error code: 401 - Unauthorized"),
        ]
        cfg = AIConfig(provider="deepseek", model="deepseek-chat",
                       api_key="sk-1", api_keys=["sk-1", "sk-2"])
        engine = AIEngine(cfg)

        with pytest.raises(KeyPoolExhaustedError) as info:
            engine.chat(create_conversation("chat"), stream=False)
        assert "exhausted" in str(info.value).lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_no_failover_for_non_deepseek(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 402 - Insufficient Balance"
        )
        cfg = AIConfig(provider="openai", model="gpt-4o",
                       api_key="sk-1", api_keys=["sk-1", "sk-2"])
        engine = AIEngine(cfg)

        with pytest.raises(Exception) as info:
            engine.chat(create_conversation("chat"), stream=False)
        assert "402" in str(info.value)
        assert mock_client.chat.completions.create.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -k "BlockingFailover" -v`
Expected: FAIL — the second `create` is never retried (`call_count == 1`), so `test_rotates_on_out_of_credit` errors out of `_blocking_chat`.

- [ ] **Step 3: Implement**

3a. In `AIEngine.__init__`, after `self._setup_client()`, add rotation state:

```python
        self.on_notice: Optional[Callable[[str], None]] = None
        self._bad: Dict[str, str] = {}  # session-only: key -> failure reason
```

3b. Add these members to `AIEngine` (place above `chat`):

```python
    @property
    def _failover_enabled(self) -> bool:
        return self.config.provider == "deepseek" and len([k for k in self.config.api_keys if k]) > 1

    @property
    def bad_keys(self) -> Dict[str, str]:
        """Session-only map of pool keys that have failed → reason."""
        return dict(self._bad)

    def _key_index(self, key: str) -> int:
        try:
            return self.config.api_keys.index(key) + 1
        except ValueError:
            return 0

    def _next_good_key(self) -> Optional[str]:
        for k in self.config.api_keys:
            if k and k not in self._bad:
                return k
        return None

    def _activate(self, key: str) -> None:
        self.config.api_key = key
        self._setup_client()

    def _exhausted_message(self) -> str:
        lines = [f"  • {mask_key(k)}: {self._bad.get(k, 'unknown')}"
                 for k in self.config.api_keys if k]
        return ("All DeepSeek keys are exhausted or invalid:\n"
                + "\n".join(lines)
                + "\n\nAdd a working key with: /key add <key>")

    def _maybe_rotate(self, exc: Exception) -> bool:
        """Rotate to the next good key after a key-related failure.

        Returns True if rotation happened (caller should retry), False if the
        error is transient / not key-related or failover is disabled. Raises
        KeyPoolExhaustedError when no usable key remains.
        """
        if not self._failover_enabled:
            return False
        reason = self._key_failure_reason(exc)
        if reason is None:
            return False
        bad_key = self.config.api_key
        self._bad[bad_key] = reason
        nxt = self._next_good_key()
        if nxt is None:
            raise KeyPoolExhaustedError(self._exhausted_message()) from exc
        prev_n = self._key_index(bad_key)
        self._activate(nxt)
        if self.on_notice:
            self.on_notice(f"DeepSeek key #{prev_n} {reason} — switched to key #{self._key_index(nxt)}")
        return True
```

3c. Replace the body of `_blocking_chat` with a failover loop:

```python
    def _blocking_chat(self, messages: List[Dict[str, str]]) -> str:
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                if not self._maybe_rotate(exc):
                    raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -k "BlockingFailover" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add hackbot/core/engine.py tests/test_engine.py
git commit -m "$(printf 'feat(engine): DeepSeek key failover for blocking calls\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 5: Engine — streaming failover

**Files:**
- Modify: `hackbot/core/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_engine.py`:

```python
def _chunk(text):
    c = MagicMock()
    c.choices = [MagicMock()]
    c.choices[0].delta.content = text
    return c


class TestStreamingFailover:
    @patch("hackbot.core.engine.OpenAI")
    def test_retries_before_first_token(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            Exception("Error code: 402 - Insufficient Balance"),
            iter([_chunk("hi"), _chunk(" there")]),
        ]
        cfg = AIConfig(provider="deepseek", model="deepseek-chat",
                       api_key="sk-1", api_keys=["sk-1", "sk-2"])
        engine = AIEngine(cfg)
        tokens = []

        result = engine.chat(create_conversation("chat"), stream=True, on_token=tokens.append)

        assert result == "hi there"
        assert tokens == ["hi", " there"]
        assert cfg.api_key == "sk-2"

    @patch("hackbot.core.engine.OpenAI")
    def test_no_retry_after_first_token(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        def gen():
            yield _chunk("partial")
            raise Exception("Error code: 402 - Insufficient Balance")

        mock_client.chat.completions.create.return_value = gen()
        cfg = AIConfig(provider="deepseek", model="deepseek-chat",
                       api_key="sk-1", api_keys=["sk-1", "sk-2"])
        engine = AIEngine(cfg)
        tokens = []

        with pytest.raises(Exception) as info:
            engine.chat(create_conversation("chat"), stream=True, on_token=tokens.append)

        assert "402" in str(info.value)
        assert tokens == ["partial"]
        assert mock_client.chat.completions.create.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -k "StreamingFailover" -v`
Expected: FAIL — `test_retries_before_first_token` raises instead of rotating.

- [ ] **Step 3: Implement**

Replace the body of `_stream_chat` with a failover loop that only retries before the first token is emitted:

```python
    def _stream_chat(
        self,
        messages: List[Dict[str, str]],
        on_token: Callable[[str], None],
    ) -> str:
        while True:
            emitted = False
            parts: List[str] = []
            try:
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        emitted = True
                        parts.append(token)
                        on_token(token)
                return "".join(parts)
            except Exception as exc:
                # Already streamed output — retrying would duplicate it.
                if emitted:
                    raise
                if not self._maybe_rotate(exc):
                    raise
                # rotated to a fresh key — retry the request from the top
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -v`
Expected: PASS (all engine tests, including the 13 existing `validate_api_key` tests).

- [ ] **Step 5: Commit**

```bash
git add hackbot/core/engine.py tests/test_engine.py
git commit -m "$(printf 'feat(engine): DeepSeek key failover for streaming calls\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 6: CLI — `_rebuild_engine` helper & notice wiring

**Files:**
- Modify: `hackbot/cli.py`

This refactor introduces one helper that rebuilds the engine *and* wires the rotation notice to `print_warning`, then routes the two existing rebuild sites through it. (`_set_key` is rewritten in Task 7 and will use the same helper.)

- [ ] **Step 1: Add the helper**

In `hackbot/cli.py`, add this method to `HackBotApp` (place it just above `_show_config`):

```python
    def _rebuild_engine(self) -> None:
        """Rebuild the AI engine from current config and re-wire it to all modes."""
        self.engine = AIEngine(self.config.ai)
        self.engine.on_notice = lambda msg: print_warning(msg)
        self.chat.engine = self.engine
        self.plan.engine = self.engine
        if self.agent:
            self.agent.engine = self.engine
            self.agent.summarizer.engine = self.engine
```

- [ ] **Step 2: Wire the notice on the initial engine**

In `HackBotApp.__init__`, immediately after `self._start_time = time.time()`, add:

```python
        self.engine.on_notice = lambda msg: print_warning(msg)
```

- [ ] **Step 3: Route `_set_model` through the helper**

In `_set_model`, replace these lines:

```python
        self.config.ai.model = model
        self.engine = AIEngine(self.config.ai)
        # Update all modes with new engine
        self.chat.engine = self.engine
        self.plan.engine = self.engine
        if self.agent:
            self.agent.engine = self.engine
            self.agent.summarizer.engine = self.engine
        save_config(self.config)
```

with:

```python
        self.config.ai.model = model
        self._rebuild_engine()
        save_config(self.config)
```

- [ ] **Step 4: Route `_set_provider` through the helper**

In `_set_provider`, replace these lines:

```python
        self.engine = AIEngine(self.config.ai)
        self.chat.engine = self.engine
        self.plan.engine = self.engine
        if self.agent:
            self.agent.engine = self.engine
            self.agent.summarizer.engine = self.engine
        save_config(self.config)
```

with:

```python
        self._rebuild_engine()
        save_config(self.config)
```

- [ ] **Step 5: Verify nothing regressed**

Run: `python -c "from hackbot.cli import HackBotApp; from hackbot.config import HackBotConfig; a = HackBotApp(HackBotConfig()); print('on_notice wired:', callable(a.engine.on_notice))"`
Expected: `on_notice wired: True`

Run: `pytest tests/ -q`
Expected: PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add hackbot/cli.py
git commit -m "$(printf 'refactor(cli): add _rebuild_engine helper and wire rotation notices\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 7: CLI — `/key` subcommands, `/keys`, and help text

**Files:**
- Modify: `hackbot/cli.py`, `hackbot/ui/__init__.py`
- Test: `tests/test_keypool_cli.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_keypool_cli.py`:

```python
"""Tests for the DeepSeek key-pool REPL commands."""

from unittest.mock import MagicMock, patch

import pytest

from hackbot.cli import HackBotApp
from hackbot.config import HackBotConfig


def _app(provider="deepseek", keys=None, active=""):
    cfg = HackBotConfig()
    cfg.ai.provider = provider
    cfg.ai.model = "deepseek-chat" if provider == "deepseek" else "gpt-4o"
    cfg.ai.api_keys = list(keys or [])
    cfg.ai.api_key = active or (cfg.ai.api_keys[0] if cfg.ai.api_keys else "")
    return HackBotApp(cfg)


@patch("hackbot.cli.save_config")
@patch("hackbot.core.engine.OpenAI")
def test_key_add_appends(mock_openai, mock_save):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(model="deepseek-chat")
    app = _app(keys=["sk-1"], active="sk-1")

    app._set_key("add sk-2")

    assert app.config.ai.api_keys == ["sk-1", "sk-2"]
    assert mock_save.called


@patch("hackbot.cli.save_config")
@patch("hackbot.core.engine.OpenAI")
def test_key_add_guarded_on_non_deepseek(mock_openai, mock_save):
    mock_openai.return_value = MagicMock()
    app = _app(provider="openai", keys=["sk-1"], active="sk-1")

    app._set_key("add sk-2")

    assert app.config.ai.api_keys == ["sk-1"]  # unchanged
    assert not mock_save.called


@patch("hackbot.cli.save_config")
@patch("hackbot.core.engine.OpenAI")
def test_key_remove(mock_openai, mock_save):
    mock_openai.return_value = MagicMock()
    app = _app(keys=["sk-1", "sk-2"], active="sk-1")

    app._set_key("remove 1")

    assert app.config.ai.api_keys == ["sk-2"]
    assert app.config.ai.api_key == "sk-2"


@patch("hackbot.cli.save_config")
@patch("hackbot.core.engine.OpenAI")
def test_bare_key_sets_active_front(mock_openai, mock_save):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(model="deepseek-chat")
    app = _app(keys=["sk-1", "sk-2"], active="sk-1")

    app._set_key("sk-2")

    assert app.config.ai.api_keys == ["sk-2", "sk-1"]
    assert app.config.ai.api_key == "sk-2"


@patch("hackbot.cli.save_config")
@patch("hackbot.core.engine.OpenAI")
def test_list_keys_runs(mock_openai, mock_save):
    mock_openai.return_value = MagicMock()
    app = _app(keys=["sk-1", "sk-2"], active="sk-1")

    assert app._list_keys() is True  # does not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_keypool_cli.py -v`
Expected: FAIL — `_set_key("add sk-2")` currently treats `"add sk-2"` as a literal key; `_list_keys` does not exist.

- [ ] **Step 3: Extend the config import in `cli.py`**

Change the existing `from hackbot.config import (...)` block to add the four new names:

```python
from hackbot.config import (
    CONFIG_DIR,
    HackBotConfig,
    AIConfig,
    add_key,
    detect_platform,
    detect_tools,
    load_config,
    mask_key,
    remove_key,
    save_config,
    set_active_key,
)
```

- [ ] **Step 4: Rewrite `_set_key` with subcommand routing**

Replace the entire existing `_set_key` method with:

```python
    def _set_key(self, args: str) -> bool:
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else ""
        rest = parts[1].strip() if len(parts) > 1 else ""

        if sub == "add":
            return self._key_add(rest)
        if sub == "remove":
            return self._key_remove(rest)
        if sub == "list":
            return self._list_keys()

        key = args.strip()
        if not key:
            print_error(
                "Usage: /key <api-key>        Set the active API key\n"
                "       /key add <api-key>    Add a DeepSeek key to the pool\n"
                "       /key remove <n>       Remove DeepSeek key #n\n"
                "       /keys                 List the DeepSeek key pool"
            )
            return True

        if self.config.ai.provider == "deepseek":
            set_active_key(self.config.ai, key)
        else:
            self.config.ai.api_key = key
        self._rebuild_engine()

        print_info("Validating API key...")
        result = self.engine.validate_api_key()
        if result["valid"]:
            save_config(self.config)
            print_success(result["message"])
        else:
            print_error(result["message"])
            print_warning("API key saved but may not work. Use /key to set a valid key.")
            save_config(self.config)
        return True

    def _key_add(self, key: str) -> bool:
        if self.config.ai.provider != "deepseek":
            print_error("Multi-key pooling is DeepSeek-only — switch with /provider deepseek.")
            return True
        key = key.strip()
        if not key:
            print_error("Usage: /key add <api-key>")
            return True
        if key in self.config.ai.api_keys:
            print_info(f"Key {mask_key(key)} is already in the pool.")
            return True

        print_info("Validating API key...")
        probe = AIEngine(AIConfig(provider="deepseek", model=self.config.ai.model, api_key=key))
        result = probe.validate_api_key()
        if result["valid"]:
            print_success(result["message"])
        else:
            print_warning(f"{result['message']} — adding anyway.")

        add_key(self.config.ai, key)
        self._rebuild_engine()
        save_config(self.config)
        print_success(f"Added DeepSeek key {mask_key(key)} (pool size: {len(self.config.ai.api_keys)}).")
        return True

    def _key_remove(self, arg: str) -> bool:
        if self.config.ai.provider != "deepseek":
            print_error("Multi-key pooling is DeepSeek-only — switch with /provider deepseek.")
            return True
        arg = arg.strip()
        if not arg.isdigit():
            print_error("Usage: /key remove <n>   (see numbers with /keys)")
            return True
        try:
            removed = remove_key(self.config.ai, int(arg) - 1)
        except IndexError:
            print_error(f"No key #{arg} in the pool (see /keys).")
            return True
        self._rebuild_engine()
        save_config(self.config)
        print_success(f"Removed DeepSeek key {mask_key(removed)}.")
        if not self.config.ai.api_keys:
            print_warning("Key pool is now empty. Add one with /key add <key>.")
        return True

    def _list_keys(self) -> bool:
        if self.config.ai.provider != "deepseek":
            print_info(
                "Multi-key pooling is DeepSeek-only. "
                f"Active key: {mask_key(self.config.ai.api_key)}"
            )
            return True
        keys = self.config.ai.api_keys
        if not keys:
            print_info("No DeepSeek keys configured. Add one with /key add <key>.")
            return True
        bad = self.engine.bad_keys
        console.print("\n[bold]DeepSeek key pool:[/]")
        for i, k in enumerate(keys, 1):
            active = "[green]●[/]" if k == self.config.ai.api_key else " "
            status = f"  [red]✗ {bad[k]}[/]" if k in bad else ""
            console.print(f"  {active} #{i}  {mask_key(k)}{status}")
        print_info(f"{len(keys)} key(s). ● = active.")
        return True
```

- [ ] **Step 5: Register `/keys` in the dispatch table**

In `_handle_command`, in the `commands = { ... }` dict, add this entry directly after the `"/key": ...` line:

```python
            "/keys": lambda: self._list_keys(),
```

- [ ] **Step 6: Add the commands to `/help`**

In `hackbot/ui/__init__.py`, inside `show_help`, replace this line:

```python
  /key <api_key>     Set API key
```

with:

```python
  /key <api_key>     Set API key
  /keys              List DeepSeek key pool (active / bad)
  /key add <key>     Add a DeepSeek key to the pool
  /key remove <n>    Remove DeepSeek key #n from the pool
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_keypool_cli.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add hackbot/cli.py hackbot/ui/__init__.py tests/test_keypool_cli.py
git commit -m "$(printf 'feat(cli): DeepSeek key pool commands (/key add, /keys, /key remove)\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 8: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `pytest tests/ -q`
Expected: PASS — all tests green, including the new config/engine/cli pool tests.

- [ ] **Step 2: Lint & format**

Run: `ruff check hackbot/ tests/`
Expected: no errors. If import-order (I) issues appear, run `ruff check --fix hackbot/ tests/` and re-run.

Run: `black hackbot/ tests/`
Expected: files already formatted (or reformatted cleanly).

- [ ] **Step 3: Type check (non-blocking, as in CI)**

Run: `mypy hackbot/ --ignore-missing-imports`
Expected: no new errors introduced by these changes.

- [ ] **Step 4: Manual REPL smoke test**

With two real DeepSeek keys (one valid, one anything), run `hackbot` and enter:

```text
/provider deepseek
/key <VALID_DEEPSEEK_KEY>
/key add <SECOND_DEEPSEEK_KEY>
/keys
/key remove 2
/keys
```

Expected:
- `/keys` lists the pool masked, with `●` on the active key.
- `/key remove 2` removes the second key; the follow-up `/keys` shows one key.
- On another provider (e.g. `/provider openai` then `/key add x`), the command prints the DeepSeek-only guard message and does not modify anything.

- [ ] **Step 5: Final commit (only if lint/format changed files)**

```bash
git add -A
git commit -m "$(printf 'chore: lint/format pass for DeepSeek key failover\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Notes / deviations from spec

- **`validate_api_key()` is left intact** rather than rewritten to call the new
  classifier. Its categorization serves a different purpose (user-facing
  validation messages: it reports rate-limits as *valid*, and distinguishes
  404/timeout). `_key_failure_reason` is a focused sibling that reads the same
  signals (status code + message markers) for rotation decisions, so the two do
  not drift. The 13 existing validation tests stay green.
- **No standalone `_with_failover(do_call)` wrapper.** Blocking and streaming
  retries have different shapes (streaming must not retry once a token is
  emitted), so the shared rotation logic lives in `_maybe_rotate()`, which both
  `_blocking_chat` and `_stream_chat` call. This preserves the spec's
  single-source-of-truth intent.
- **CLI tests added** (`tests/test_keypool_cli.py`) beyond the spec's
  engine+config testing scope — cheap, no-network coverage of the new commands.
- **No `refresh_pool()` method** (the spec named one). Every CLI pool edit calls
  `_rebuild_engine()`, which constructs a fresh `AIEngine` with empty bad-key
  state, so a separate refresh method would be dead code. The spec's intent —
  the engine reflects pool edits made by a command — is preserved.
```
