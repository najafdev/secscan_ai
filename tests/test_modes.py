"""Tests for HackBot modes."""

import pytest

from hackbot.modes.plan import PlanMode, PLAN_TEMPLATES
from hackbot.modes.agent import AgentMode, Severity, Finding
import hackbot.modes.agent as agent_mod
from hackbot.core.engine import AIEngine
from hackbot.config import HackBotConfig, AgentConfig, AIConfig
from hackbot.core.runner import ToolResult
from unittest.mock import MagicMock, patch


def test_plan_templates_exist():
    """Test that plan templates are available."""
    templates = PlanMode.list_templates()
    assert "web_pentest" in templates
    assert "network_pentest" in templates
    assert "api_pentest" in templates
    assert "cloud_audit" in templates
    assert "red_team" in templates
    assert "bug_bounty" in templates


def test_plan_templates_have_phases():
    """Test that each template has phases."""
    for key, template in PLAN_TEMPLATES.items():
        assert "name" in template
        assert "phases" in template
        assert len(template["phases"]) > 0


def test_severity_enum():
    """Test Severity enum values."""
    assert Severity.CRITICAL.value == "Critical"
    assert Severity.HIGH.value == "High"
    assert Severity.MEDIUM.value == "Medium"
    assert Severity.LOW.value == "Low"
    assert Severity.INFO.value == "Info"


def test_finding_creation():
    """Test Finding dataclass."""
    finding = Finding(
        title="SQL Injection",
        severity=Severity.HIGH,
        description="Found SQL injection in login form",
        evidence="' OR '1'='1",
        recommendation="Use parameterized queries",
    )
    assert finding.title == "SQL Injection"
    assert finding.severity == Severity.HIGH

    d = finding.to_dict()
    assert d["severity"] == "High"
    assert d["title"] == "SQL Injection"


@pytest.fixture
def mock_agent():
    """Create an AgentMode instance with mocked dependencies for testing loop logic."""
    config = HackBotConfig()
    config.ai = AIConfig(provider="mock", model="mock")
    config.agent = AgentConfig(allowed_tools=["echo", "nmap"], safe_mode=False)

    engine = MagicMock(spec=AIEngine)
    engine.chat.return_value = "Mocked AI response"

    with patch("hackbot.core.vulndb.VulnDB"), patch("hackbot.core.cve.CVELookup"):
        agent = AgentMode(engine=engine, config=config)
        agent.target = "127.0.0.1"
        agent.conversation = MagicMock()
        agent.is_running = True
        return agent


def test_process_actions_loop_skips_same_round_duplicates(mock_agent):
    """Test that identical commands within one round are skipped."""
    mock_agent._execute_action = MagicMock(
        return_value=(
            "output",
            ToolResult(
                tool="echo",
                command="echo test",
                stdout="test",
                stderr="",
                return_code=0,
                duration=0.1,
                success=True,
            ),
        )
    )

    actions = [
        {"action": "execute", "command": "echo test"},
        {"action": "execute", "command": "echo test"},
        {"action": "execute", "command": "echo test"},
    ]

    # We only care about the single-round processing here, so mock Chat to stop the loop
    mock_agent.engine.chat.return_value = '{"action": "complete"}'

    mock_agent._process_actions_loop("Mocked AI response", actions, max_rounds=2)

    # execute_action should only be called once, the others are deduplicated in same round
    assert mock_agent._execute_action.call_count == 1


def test_process_actions_loop_skips_session_duplicates(mock_agent):
    """Test that commands executed >=2 times in a session are skipped."""
    mock_agent._command_history = {"echo test": 2}  # Already run twice

    mock_agent._execute_action = MagicMock()
    mock_agent.engine.chat.return_value = '{"action": "complete"}'

    actions = [
        {"action": "execute", "command": "echo test"},
    ]
    mock_agent._process_actions_loop("Mocked AI response", actions, max_rounds=2)

    # Should be skipped entirely
    mock_agent._execute_action.assert_not_called()


def test_command_history_increments(mock_agent):
    """Test that executing an action increments command history."""
    # Ensure runner is a mock that won't actually execute
    mock_agent.runner = MagicMock()
    mock_agent.runner.execute.return_value = ToolResult(
        tool="echo",
        command="echo hello",
        stdout="hello",
        stderr="",
        return_code=0,
        duration=0.1,
        success=True,
    )

    action = {"action": "execute", "command": "echo hello"}

    assert "echo hello" not in mock_agent._command_history
    mock_agent._execute_action(action)
    assert mock_agent._command_history["echo hello"] == 1

    mock_agent._execute_action(action)
    assert mock_agent._command_history["echo hello"] == 2


def test_should_nudge_capped_per_step(mock_agent):
    """Test that _should_nudge only returns True once per step."""
    response_with_tool = "I will run nmap now."

    # First check should be True
    assert mock_agent._should_nudge(response_with_tool) is True
    # Second check should be False (already nudged)
    assert mock_agent._should_nudge(response_with_tool) is False

    # Reset count (as happens at top of step())
    mock_agent._nudge_count = 0
    assert mock_agent._should_nudge(response_with_tool) is True


def test_should_nudge_ignores_non_tools(mock_agent):
    """Test that _should_nudge returns False if no tool names are present."""
    response_no_tool = "I have begun assessing the target based on the scope provided."
    # Should be false since it doesn't mention nmap/sqlmap/etc
    assert mock_agent._should_nudge(response_no_tool) is False


# ---------------------------------------------------------------------------
# Install action tests
# ---------------------------------------------------------------------------


def _make_install_agent():
    """Minimal AgentMode with a stub engine; safe for unit-testing helpers."""
    config = HackBotConfig()
    config.ai = AIConfig(provider="mock", model="mock")
    config.agent = AgentConfig(allowed_tools=["echo", "nmap", "nuclei"], safe_mode=False)

    engine = MagicMock(spec=AIEngine)
    engine.chat.return_value = "Mocked AI response"

    with patch("hackbot.core.vulndb.VulnDB"), patch("hackbot.core.cve.CVELookup"):
        agent = AgentMode(engine=engine, config=config)
        agent.target = "127.0.0.1"
        agent.conversation = MagicMock()
        agent.is_running = True
        return agent


def test_parse_actions_recognizes_install(monkeypatch, tmp_path):
    a = _make_install_agent()
    actions = a._parse_actions('{"action": "install", "tool": "nuclei"}')
    assert actions == [{"action": "install", "tool": "nuclei"}]


def test_install_action_already_installed_short_circuits(monkeypatch, tmp_path):
    a = _make_install_agent()
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: "/usr/bin/nuclei")
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "already installed" in msg.lower()


def test_install_action_rejects_non_allowlisted_tool(monkeypatch, tmp_path):
    a = _make_install_agent()
    a.config.agent.allow_arbitrary_install = False
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    msg = a._process_install_action({"action": "install", "tool": "evilpkg"})
    assert "allowlist" in msg.lower()


def test_install_action_unmapped_reports_no_recipe(monkeypatch, tmp_path):
    a = _make_install_agent()
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    # gcc is not in the default allowlist, so we need to stub is_tool_allowed
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)
    msg = a._process_install_action({"action": "install", "tool": "gcc"})
    assert "no install recipe" in msg.lower()


def test_install_action_runs_installer_and_reports(monkeypatch, tmp_path):
    a = _make_install_agent()
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)

    from hackbot.core.installer import InstallPlan, InstallResult

    plan = InstallPlan("nuclei", "go", "x", ["go", "install", "x"], False)
    monkeypatch.setattr(a.installer, "plan_install", lambda t: plan)
    monkeypatch.setattr(
        a.installer,
        "install",
        lambda p: InstallResult(
            "nuclei", True, "go", "/usr/bin/nuclei", "Installed nuclei via go (/usr/bin/nuclei)"
        ),
    )
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "installed nuclei" in msg.lower()


def test_install_action_safe_mode_decline(monkeypatch, tmp_path):
    a = _make_install_agent()
    a.config.agent.safe_mode = True
    a.runner.on_confirm = lambda cmd, reason: False  # user declines
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)
    from hackbot.core.installer import InstallPlan

    plan = InstallPlan("nuclei", "go", "x", ["go", "install", "x"], False)
    monkeypatch.setattr(a.installer, "plan_install", lambda t: plan)
    called = {"installed": False}
    monkeypatch.setattr(a.installer, "install", lambda p: called.__setitem__("installed", True))
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "declined" in msg.lower()
    assert called["installed"] is False


def test_plan_mode_ask_stream_false():
    """Verify PlanMode.ask accepts stream=False and stream=True without TypeError."""
    engine = MagicMock(spec=AIEngine)
    engine.chat.return_value = "Plan test response"
    plan = PlanMode(engine=engine, config=HackBotConfig())

    # Test with stream=False (used by telegram bot handler)
    res = plan.ask("How to test SQLi?", stream=False)
    assert res == "Plan test response"

    # Test with stream=True
    res_stream = plan.ask("Next phase", stream=True)
    assert res_stream == "Plan test response"


def test_zeroday_active_cookies():
    """Verify HttpClient cookies property returns string dictionary."""
    from hackbot.core.zeroday_active import HttpClient
    client = HttpClient()
    client.session.cookies.set("session_id", "abc123xyz")
    assert client.cookies == {"session_id": "abc123xyz"}
    assert isinstance(client.cookies, dict)


def test_engine_chat_with_messages_list():
    """Verify AIEngine.chat accepts messages list directly as well as Conversation."""
    from hackbot.core.engine import AIEngine
    from hackbot.config import HackBotConfig
    engine = AIEngine(HackBotConfig().ai)
    engine._client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Chat reply"
    engine._client.chat.completions.create.return_value = mock_resp

    reply = engine.chat(messages=[{"role": "user", "content": "hello"}], stream=False)
    assert reply == "Chat reply"
