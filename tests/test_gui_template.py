from pathlib import Path

TEMPLATE = Path("hackbot/gui/templates/index.html")


def read_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_agent_auto_run_contract_exists():
    html = read_template()

    assert "let agentAutoRunActive = false;" in html
    assert "let agentActionInFlight = false;" in html
    assert "async function startAgentAutoRun()" in html
    assert "while (agentAutoRunActive && agentRunning && !agentStopRequested)" in html
    assert "const stepResult = await runAgentStep('');" in html
    assert "await startAgentAutoRun();" in html
    assert "Agent response was truncated. Click Continue to resume." in html


def test_agent_stop_cancels_auto_run():
    html = read_template()

    assert "async function agentStop()" in html
    assert "agentStopRequested = true;" in html
    assert "agentAutoRunActive = false;" in html


def test_sidebar_collapse_contract_exists():
    html = read_template()

    assert "const SIDEBAR_COLLAPSED_KEY = 'hackbot.sidebar.collapsed';" in html
    assert 'id="appRoot"' in html
    assert 'id="sidebarToggle"' in html
    assert 'aria-label="Collapse sidebar"' in html
    assert 'aria-expanded="true"' in html
    assert 'aria-controls="sidebarNav"' in html
    assert "function toggleSidebar()" in html
    assert "function initSidebarState()" in html
    assert "sidebar-collapsed" in html
    assert "localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));" in html
    assert "initSidebarState();" in html
