"""
Tests for HackBot Plugin System
==================================
"""

import inspect
import tempfile
import textwrap
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hackbot.core.plugins import (
    PluginDefinition,
    PluginManager,
    PluginResult,
    hackbot_plugin,
    get_plugin_manager,
    reset_plugin_manager,
    ensure_plugins_dir,
    PLUGINS_DIR,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the global singleton before each test."""
    reset_plugin_manager()
    yield
    reset_plugin_manager()


@pytest.fixture
def tmp_plugins_dir(tmp_path):
    """Create a temp plugins directory."""
    d = tmp_path / "plugins"
    d.mkdir()
    return d


@pytest.fixture
def manager(tmp_plugins_dir):
    """PluginManager with tmp dir."""
    return PluginManager(plugins_dir=tmp_plugins_dir)


def _write_plugin(d: Path, name: str, code: str) -> Path:
    """Helper to write a plugin file."""
    p = d / f"{name}.py"
    p.write_text(textwrap.dedent(code))
    return p


# ── PluginDefinition Tests ───────────────────────────────────────────────────

class TestPluginDefinition:
    def test_create_default(self):
        pd = PluginDefinition(name="test", description="A test", run=lambda: "ok")
        assert pd.name == "test"
        assert pd.description == "A test"
        assert pd.args == {}
        assert pd.author == ""
        assert pd.version == "1.0.0"
        assert pd.category == "custom"
        assert pd.enabled is True
        assert pd.source_path == ""

    def test_create_full(self):
        fn = lambda x: x
        pd = PluginDefinition(
            name="full", description="Full plugin", run=fn,
            args={"x": "input"}, author="tester", version="2.0",
            category="recon", enabled=False, source_path="/tmp/full.py",
        )
        assert pd.name == "full"
        assert pd.author == "tester"
        assert pd.category == "recon"
        assert pd.enabled is False
        assert pd.run is fn

    def test_to_dict(self):
        pd = PluginDefinition(
            name="ser", description="Serialize test", run=lambda: "",
            args={"a": "arg a"}, author="me", version="1.1",
            category="exploit", source_path="/tmp/ser.py",
        )
        d = pd.to_dict()
        assert d["name"] == "ser"
        assert d["description"] == "Serialize test"
        assert d["args"] == {"a": "arg a"}
        assert d["author"] == "me"
        assert d["version"] == "1.1"
        assert d["category"] == "exploit"
        assert d["enabled"] is True
        assert d["source_path"] == "/tmp/ser.py"
        assert "run" not in d  # callable not serialized

    def test_to_dict_no_callable(self):
        pd = PluginDefinition(name="x", description="x", run=lambda: "")
        d = pd.to_dict()
        assert callable(pd.run)
        assert "run" not in d


# ── PluginResult Tests ───────────────────────────────────────────────────────

class TestPluginResult:
    def test_success_result(self):
        r = PluginResult(plugin_name="foo", success=True, output="done", duration=1.23)
        assert r.success
        assert r.output == "done"
        assert r.error == ""

    def test_error_result(self):
        r = PluginResult(plugin_name="foo", success=False, output="", duration=0.1, error="boom")
        assert not r.success
        assert r.error == "boom"

    def test_to_dict(self):
        r = PluginResult(plugin_name="bar", success=True, output="ok", duration=0.123)
        d = r.to_dict()
        assert d["plugin_name"] == "bar"
        assert d["success"] is True
        assert d["output"] == "ok"
        assert d["duration"] == 0.12  # rounded
        assert "timestamp" in d

    def test_timestamp_auto(self):
        before = time.time()
        r = PluginResult(plugin_name="t", success=True, output="", duration=0)
        assert r.timestamp >= before


# ── Decorator Tests ──────────────────────────────────────────────────────────

class TestHackbotPluginDecorator:
    def test_basic_decorator(self):
        @hackbot_plugin(name="greeting", description="Says hello")
        def greet(name: str = "World") -> str:
            return f"Hello {name}"

        assert hasattr(greet, "_plugin_def")
        pd = greet._plugin_def
        assert pd.name == "greeting"
        assert pd.description == "Says hello"
        assert pd.run is greet

    def test_args_auto_extract(self):
        @hackbot_plugin(name="auto", description="Auto-args")
        def func(host: str, port: str = "80") -> str:
            return ""

        pd = func._plugin_def
        assert "host" in pd.args
        assert "port" in pd.args
        assert "default: 80" in pd.args["port"]

    def test_args_explicit(self):
        @hackbot_plugin(
            name="explicit",
            description="Explicit args",
            args={"target": "The host to scan"},
        )
        def func(target: str) -> str:
            return target

        pd = func._plugin_def
        assert pd.args == {"target": "The host to scan"}

    def test_full_decorator_options(self):
        @hackbot_plugin(
            name="full",
            description="Full plugin",
            args={"x": "param x"},
            author="tester",
            version="3.0",
            category="exploit",
        )
        def func(x: str) -> str:
            return x

        pd = func._plugin_def
        assert pd.author == "tester"
        assert pd.version == "3.0"
        assert pd.category == "exploit"

    def test_decorated_function_still_callable(self):
        @hackbot_plugin(name="call_test", description="test")
        def func(val: str = "hi") -> str:
            return f"got {val}"

        assert func("world") == "got world"
        assert func() == "got hi"


# ── PluginManager Discovery Tests ────────────────────────────────────────────

class TestPluginManagerDiscovery:
    def test_discover_empty_dir(self, manager, tmp_plugins_dir):
        count = manager.discover()
        assert count == 0
        assert len(manager.plugins) == 0

    def test_discover_nonexistent_dir(self, tmp_path):
        pm = PluginManager(plugins_dir=tmp_path / "nope")
        count = pm.discover()
        assert count == 0

    def test_discover_decorator_plugin(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "hello", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="hello", description="Says hello")
            def run(name: str = "World") -> str:
                return f"Hello {name}"
        """)
        count = manager.discover()
        assert count == 1
        assert "hello" in manager.plugins

    def test_discover_register_plugin(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "reg_plugin", """
            from hackbot.core.plugins import PluginDefinition

            def do_work(msg: str = "hi") -> str:
                return f"work: {msg}"

            def register() -> PluginDefinition:
                return PluginDefinition(
                    name="reg_plugin",
                    description="Register pattern plugin",
                    run=do_work,
                    args={"msg": "message"},
                )
        """)
        count = manager.discover()
        assert count == 1
        assert "reg_plugin" in manager.plugins
        assert manager.plugins["reg_plugin"].description == "Register pattern plugin"

    def test_discover_sets_source_path(self, manager, tmp_plugins_dir):
        p = _write_plugin(tmp_plugins_dir, "pathtest", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="pathtest", description="test")
            def run() -> str:
                return "ok"
        """)
        manager.discover()
        assert manager.plugins["pathtest"].source_path == str(p)

    def test_discover_skips_underscore(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "_private", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="hidden", description="hidden")
            def run() -> str:
                return "hidden"
        """)
        count = manager.discover()
        assert count == 0

    def test_discover_skips_non_py(self, manager, tmp_plugins_dir):
        (tmp_plugins_dir / "readme.txt").write_text("not a plugin")
        count = manager.discover()
        assert count == 0

    def test_discover_multiple_plugins(self, manager, tmp_plugins_dir):
        for i in range(3):
            _write_plugin(tmp_plugins_dir, f"plug{i}", f"""
                from hackbot.core.plugins import hackbot_plugin

                @hackbot_plugin(name="plug{i}", description="Plugin {i}")
                def run() -> str:
                    return "p{i}"
            """)
        count = manager.discover()
        assert count == 3

    def test_discover_error_handling(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "bad", """
            raise RuntimeError("broken plugin!")
        """)
        _write_plugin(tmp_plugins_dir, "good", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="good", description="works")
            def run() -> str:
                return "ok"
        """)
        count = manager.discover()
        assert count == 1
        assert "good" in manager.plugins
        errors = manager.get_load_errors()
        assert len(errors) == 1
        assert "bad.py" in errors[0]["file"]

    def test_discover_no_register_or_decorator(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "plain", """
            def some_function():
                return "hi"
        """)
        count = manager.discover()
        assert count == 0
        errors = manager.get_load_errors()
        assert len(errors) == 1
        assert "No register()" in errors[0]["error"]

    def test_discover_register_returns_wrong_type(self, manager, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "wrongtype", """
            def register():
                return {"name": "oops"}
        """)
        count = manager.discover()
        assert count == 0
        errors = manager.get_load_errors()
        assert len(errors) == 1
        assert "must return a PluginDefinition" in errors[0]["error"]


# ── PluginManager Registration Tests ─────────────────────────────────────────

class TestPluginManagerRegistration:
    def test_register_plugin(self, manager):
        pd = PluginDefinition(name="man", description="manual", run=lambda: "ok")
        manager.register(pd)
        assert "man" in manager.plugins

    def test_register_empty_name_raises(self, manager):
        pd = PluginDefinition(name="", description="no name", run=lambda: "ok")
        with pytest.raises(ValueError, match="cannot be empty"):
            manager.register(pd)

    def test_register_non_callable_raises(self, manager):
        pd = PluginDefinition(name="bad", description="bad", run="not callable")
        with pytest.raises(ValueError, match="not callable"):
            manager.register(pd)

    def test_unregister_existing(self, manager):
        pd = PluginDefinition(name="temp", description="temp", run=lambda: "ok")
        manager.register(pd)
        assert manager.unregister("temp") is True
        assert "temp" not in manager.plugins

    def test_unregister_nonexistent(self, manager):
        assert manager.unregister("nope") is False

    def test_register_overwrite(self, manager):
        pd1 = PluginDefinition(name="dup", description="first", run=lambda: "1")
        pd2 = PluginDefinition(name="dup", description="second", run=lambda: "2")
        manager.register(pd1)
        manager.register(pd2)
        assert manager.plugins["dup"].description == "second"


# ── PluginManager Execution Tests ────────────────────────────────────────────

class TestPluginManagerExecution:
    def test_execute_simple(self, manager):
        pd = PluginDefinition(name="echo", description="echo", run=lambda x="hi": f"echo: {x}")
        manager.register(pd)
        result = manager.execute("echo", x="world")
        assert result.success is True
        assert result.output == "echo: world"
        assert result.plugin_name == "echo"
        assert result.duration >= 0

    def test_execute_default_args(self, manager):
        pd = PluginDefinition(name="def", description="defaults", run=lambda x="default": x)
        manager.register(pd)
        result = manager.execute("def")
        assert result.success is True
        assert result.output == "default"

    def test_execute_not_found(self, manager):
        result = manager.execute("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    def test_execute_disabled_plugin(self, manager):
        pd = PluginDefinition(name="off", description="disabled", run=lambda: "ok", enabled=False)
        manager.register(pd)
        result = manager.execute("off")
        assert result.success is False
        assert "disabled" in result.error

    def test_execute_filters_kwargs(self, manager):
        def strict_func(host: str) -> str:
            return f"host={host}"
        pd = PluginDefinition(name="strict", description="strict", run=strict_func)
        manager.register(pd)
        # Extra kwargs should be filtered out
        result = manager.execute("strict", host="10.0.0.1", unknown_arg="garbage")
        assert result.success is True
        assert result.output == "host=10.0.0.1"

    def test_execute_runtime_error(self, manager):
        def bad_func() -> str:
            raise ValueError("kaboom")
        pd = PluginDefinition(name="boom", description="crashes", run=bad_func)
        manager.register(pd)
        result = manager.execute("boom")
        assert result.success is False
        assert "ValueError" in result.error
        assert "kaboom" in result.error

    def test_execute_non_string_result(self, manager):
        pd = PluginDefinition(name="num", description="returns int", run=lambda: 42)
        manager.register(pd)
        result = manager.execute("num")
        assert result.success is True
        assert result.output == "42"

    def test_execute_measures_duration(self, manager):
        import time as _time
        def slow_func() -> str:
            _time.sleep(0.05)
            return "done"
        pd = PluginDefinition(name="slow", description="slow", run=slow_func)
        manager.register(pd)
        result = manager.execute("slow")
        assert result.success is True
        assert result.duration >= 0.04  # allow some tolerance


# ── PluginManager Query Tests ────────────────────────────────────────────────

class TestPluginManagerQuery:
    def test_list_plugins(self, manager):
        for i in range(3):
            pd = PluginDefinition(name=f"p{i}", description=f"Plugin {i}", run=lambda: "")
            manager.register(pd)
        result = manager.list_plugins()
        assert len(result) == 3
        names = {p["name"] for p in result}
        assert names == {"p0", "p1", "p2"}

    def test_get_plugin(self, manager):
        pd = PluginDefinition(name="get_me", description="get test", run=lambda: "")
        manager.register(pd)
        got = manager.get_plugin("get_me")
        assert got is pd
        assert manager.get_plugin("nope") is None

    def test_get_plugin_names(self, manager):
        for n in ("alpha", "beta", "gamma"):
            pd = PluginDefinition(name=n, description=n, run=lambda: "")
            manager.register(pd)
        names = manager.get_plugin_names()
        assert set(names) == {"alpha", "beta", "gamma"}

    def test_count_properties(self, manager):
        pd1 = PluginDefinition(name="e1", description="enabled", run=lambda: "")
        pd2 = PluginDefinition(name="e2", description="disabled", run=lambda: "", enabled=False)
        manager.register(pd1)
        manager.register(pd2)
        assert manager.count == 2
        assert manager.enabled_count == 1

    def test_get_agent_tool_descriptions_empty(self, manager):
        assert manager.get_agent_tool_descriptions() == ""

    def test_get_agent_tool_descriptions(self, manager):
        pd = PluginDefinition(
            name="scanner", description="Scans stuff",
            run=lambda target: "",
            args={"target": "Host to scan"},
            category="recon",
        )
        manager.register(pd)
        desc = manager.get_agent_tool_descriptions()
        assert "scanner" in desc
        assert "Scans stuff" in desc
        assert "--target" in desc
        assert "CUSTOM PLUGINS" in desc

    def test_get_agent_tool_descriptions_skips_disabled(self, manager):
        pd1 = PluginDefinition(name="on", description="on", run=lambda: "", args={"x": "x"})
        pd2 = PluginDefinition(name="off", description="off", run=lambda: "", enabled=False)
        manager.register(pd1)
        manager.register(pd2)
        desc = manager.get_agent_tool_descriptions()
        assert "on" in desc
        assert "off" not in desc


# ── Singleton Tests ──────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_plugin_manager_creates_once(self, tmp_plugins_dir):
        pm1 = get_plugin_manager(plugins_dir=tmp_plugins_dir)
        pm2 = get_plugin_manager(plugins_dir=tmp_plugins_dir)
        assert pm1 is pm2

    def test_reset_plugin_manager(self, tmp_plugins_dir):
        pm1 = get_plugin_manager(plugins_dir=tmp_plugins_dir)
        reset_plugin_manager()
        pm2 = get_plugin_manager(plugins_dir=tmp_plugins_dir)
        assert pm1 is not pm2

    def test_get_plugin_manager_auto_discovers(self, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "auto_disc", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="auto_disc", description="auto")
            def run() -> str:
                return "ok"
        """)
        pm = get_plugin_manager(plugins_dir=tmp_plugins_dir)
        assert "auto_disc" in pm.plugins


# ── ensure_plugins_dir Tests ─────────────────────────────────────────────────

class TestEnsurePluginsDir:
    def test_creates_dir(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "config" / "hackbot" / "plugins"
        monkeypatch.setattr("hackbot.core.plugins.PLUGINS_DIR", test_dir)
        result = ensure_plugins_dir()
        assert result == test_dir
        assert test_dir.exists()

    def test_idempotent(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "plugins"
        test_dir.mkdir()
        monkeypatch.setattr("hackbot.core.plugins.PLUGINS_DIR", test_dir)
        result = ensure_plugins_dir()
        assert result == test_dir


# ── Integration Tests ────────────────────────────────────────────────────────

class TestIntegration:
    def test_discover_and_execute_decorator_plugin(self, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "adder", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(
                name="adder",
                description="Adds two numbers",
                args={"a": "First number", "b": "Second number"},
            )
            def run(a: str = "0", b: str = "0") -> str:
                return str(int(a) + int(b))
        """)
        pm = PluginManager(plugins_dir=tmp_plugins_dir)
        pm.discover()
        result = pm.execute("adder", a="3", b="7")
        assert result.success is True
        assert result.output == "10"

    def test_discover_and_execute_register_plugin(self, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "greeter", """
            from hackbot.core.plugins import PluginDefinition

            def greet(person: str = "World") -> str:
                return f"Hello, {person}!"

            def register():
                return PluginDefinition(
                    name="greeter",
                    description="Greets someone",
                    run=greet,
                    args={"person": "Person to greet"},
                    author="tester",
                )
        """)
        pm = PluginManager(plugins_dir=tmp_plugins_dir)
        pm.discover()
        result = pm.execute("greeter", person="Alice")
        assert result.success is True
        assert result.output == "Hello, Alice!"
        assert pm.plugins["greeter"].author == "tester"

    def test_full_lifecycle(self, tmp_plugins_dir):
        """Test discover -> list -> execute -> unregister lifecycle."""
        _write_plugin(tmp_plugins_dir, "lifecycle", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="lifecycle", description="Lifecycle test")
            def run() -> str:
                return "alive"
        """)
        pm = PluginManager(plugins_dir=tmp_plugins_dir)

        # Discover
        count = pm.discover()
        assert count == 1

        # List
        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "lifecycle"

        # Execute
        result = pm.execute("lifecycle")
        assert result.success is True
        assert result.output == "alive"

        # Unregister
        assert pm.unregister("lifecycle") is True
        assert pm.count == 0

        # Execute after unregister
        result = pm.execute("lifecycle")
        assert result.success is False

    def test_rediscover_picks_up_new_plugins(self, tmp_plugins_dir):
        pm = PluginManager(plugins_dir=tmp_plugins_dir)
        assert pm.discover() == 0

        _write_plugin(tmp_plugins_dir, "late", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="late", description="Late arrival")
            def run() -> str:
                return "better late"
        """)
        # Clear existing and rediscover
        pm.plugins.clear()
        assert pm.discover() == 1
        assert "late" in pm.plugins

    def test_plugin_with_complex_output(self, tmp_plugins_dir):
        _write_plugin(tmp_plugins_dir, "multiline", """
            from hackbot.core.plugins import hackbot_plugin

            @hackbot_plugin(name="multiline", description="Multiline output")
            def run(target: str = "dummy") -> str:
                lines = [
                    f"Scanning {target}...",
                    "Port 22: OPEN",
                    "Port 80: OPEN",
                    "Port 443: CLOSED",
                    "Scan complete.",
                ]
                return chr(10).join(lines)
        """)
        pm = PluginManager(plugins_dir=tmp_plugins_dir)
        pm.discover()
        result = pm.execute("multiline", target="10.0.0.1")
        assert result.success is True
        assert "Scanning 10.0.0.1" in result.output
        assert result.output.count("\n") == 4
