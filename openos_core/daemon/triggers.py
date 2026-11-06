"""
OpenOS Trigger Engine.

Evaluates SystemEvents against configurable trigger rules. When a rule matches,
it returns the rule so the ProactiveAgent can execute the associated action.

Rules are loaded from YAML files — built-in defaults are merged with user
overrides from ~/.config/openos/triggers.yaml.

Condition evaluation uses a safe mini-parser (no eval/exec) supporting:
  - Comparisons: percentage < 10, state == "connected"
  - Logical:     percentage < 15 and discharging == true
  - Contains:    app_name contains "code"
"""

from __future__ import annotations

import logging
import operator
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from openos_core.config import OPENOS_CONFIG_DIR, DaemonConfig
from openos_core.daemon.events import EventType, SystemEvent

logger = logging.getLogger(__name__)

# Path to built-in default triggers
_DEFAULT_TRIGGERS_FILE = Path(__file__).parent / "default_triggers.yaml"
# User override path
_USER_TRIGGERS_FILE = OPENOS_CONFIG_DIR / "triggers.yaml"


@dataclass
class TriggerRule:
    """A single proactive trigger rule."""

    name: str
    event_type: EventType
    condition: str = ""              # Safe expression to evaluate against event data
    action: str = ""                 # Natural language prompt for the Brain (empty = no Brain call)
    cooldown: int = 300              # Seconds between repeated firings
    enabled: bool = True
    notify: bool = True              # Whether to send a desktop notification
    notification_message: str = ""   # Template with {data_key} placeholders
    require_confirmation: bool = False  # If True, notify only — don't auto-execute

    # Runtime tracking (not serialized)
    _last_fired: float = field(default=0.0, repr=False)


class TriggerEngine:
    """
    Evaluates system events against trigger rules.

    Thread-safe: evaluate() can be called from any coroutine.
    """

    def __init__(self, rules: list[TriggerRule]) -> None:
        self._rules = rules
        logger.info(f"Trigger engine loaded with {len(rules)} rules")
        for r in rules:
            status = "enabled" if r.enabled else "disabled"
            logger.debug(f"  Rule: {r.name} ({r.event_type.value}) [{status}]")

    @classmethod
    def load_rules(cls, daemon_config: DaemonConfig) -> TriggerEngine:
        """Load trigger rules from default + user YAML files."""
        rules: list[TriggerRule] = []

        # Load built-in defaults
        if _DEFAULT_TRIGGERS_FILE.exists():
            rules.extend(_parse_yaml_rules(_DEFAULT_TRIGGERS_FILE))
            logger.info(f"Loaded {len(rules)} default trigger rules")

        # Merge user overrides
        user_file = Path(daemon_config.triggers_file) if daemon_config.triggers_file else _USER_TRIGGERS_FILE
        if user_file.exists():
            user_rules = _parse_yaml_rules(user_file)
            # User rules override defaults by name
            rules_by_name = {r.name: r for r in rules}
            for ur in user_rules:
                rules_by_name[ur.name] = ur
            rules = list(rules_by_name.values())
            logger.info(f"Merged {len(user_rules)} user trigger overrides")

        return cls(rules)

    def evaluate(self, event: SystemEvent) -> TriggerRule | None:
        """
        Check if any rule matches the given event.

        Returns the first matching rule, or None.
        Rules are checked in order; cooldown prevents re-firing.
        """
        now = time.time()

        for rule in self._rules:
            if not rule.enabled:
                continue

            # Event type must match
            if rule.event_type != event.event_type:
                continue

            # Check cooldown
            if now - rule._last_fired < rule.cooldown:
                continue

            # Evaluate condition (if any)
            if rule.condition:
                if not _check_condition(rule.condition, event.data):
                    continue

            # Rule matched!
            rule._last_fired = now
            logger.info(f"Trigger matched: {rule.name} for event {event.event_type.value}")
            return rule

        return None

    @property
    def rules(self) -> list[TriggerRule]:
        return list(self._rules)


# ─── YAML Parsing ────────────────────────────────────────────────────


def _parse_yaml_rules(path: Path) -> list[TriggerRule]:
    """Parse trigger rules from a YAML file."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to parse triggers YAML ({path}): {e}")
        return []

    if not data or "triggers" not in data:
        return []

    rules = []
    for item in data["triggers"]:
        try:
            event_type = EventType(item["event"])
            rules.append(TriggerRule(
                name=item["name"],
                event_type=event_type,
                condition=item.get("condition", ""),
                action=item.get("action", "").strip(),
                cooldown=item.get("cooldown", 300),
                enabled=item.get("enabled", True),
                notify=item.get("notify", True),
                notification_message=item.get("notification", ""),
                require_confirmation=item.get("require_confirmation", False),
            ))
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping invalid trigger rule: {e} — {item}")

    return rules


# ─── Safe Condition Evaluator ────────────────────────────────────────

# Supported operators
_OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

# Pattern: <key> <operator> <value>
_COMPARISON_RE = re.compile(
    r"(\w+)\s*(<=|>=|<|>|==|!=)\s*(.+)"
)

# Pattern: <key> contains <value>
_CONTAINS_RE = re.compile(
    r"(\w+)\s+contains\s+['\"](.+?)['\"]",
    re.IGNORECASE,
)


def _parse_value(raw: str) -> Any:
    """Parse a literal value from a condition string."""
    raw = raw.strip().strip("'\"")

    # Boolean
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False

    # Integer
    try:
        return int(raw)
    except ValueError:
        pass

    # Float
    try:
        return float(raw)
    except ValueError:
        pass

    # String
    return raw


def _check_condition(condition: str, data: dict[str, Any]) -> bool:
    """
    Safely evaluate a condition string against event data.

    Supports:
      - "percentage < 10"
      - "state == 'connected'"
      - "percentage < 15 and discharging == true"
      - "app_name contains 'code'"

    No eval() is used — only explicit pattern matching.
    """
    # Split on " and " / " or " for compound conditions
    if " and " in condition:
        parts = condition.split(" and ")
        return all(_check_single_condition(p.strip(), data) for p in parts)
    elif " or " in condition:
        parts = condition.split(" or ")
        return any(_check_single_condition(p.strip(), data) for p in parts)
    else:
        return _check_single_condition(condition.strip(), data)


def _check_single_condition(cond: str, data: dict[str, Any]) -> bool:
    """Evaluate a single comparison or contains expression."""
    # Try "contains" first
    m = _CONTAINS_RE.match(cond)
    if m:
        key, needle = m.group(1), m.group(2)
        value = data.get(key, "")
        return needle.lower() in str(value).lower()

    # Try comparison operators
    m = _COMPARISON_RE.match(cond)
    if m:
        key, op_str, raw_val = m.group(1), m.group(2), m.group(3)
        if key not in data:
            return False
        op_fn = _OPS.get(op_str)
        if not op_fn:
            return False
        try:
            return bool(op_fn(data[key], _parse_value(raw_val)))
        except (TypeError, ValueError):
            return False

    logger.warning(f"Could not parse condition: {cond}")
    return False
