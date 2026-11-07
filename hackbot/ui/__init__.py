"""
HackBot Terminal UI
===================
Rich terminal interface with beautiful formatting, banners, progress indicators,
and interactive prompts. Cross-platform compatible.
"""

from __future__ import annotations

import platform
from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

from hackbot import __version__

# ── Theme ────────────────────────────────────────────────────────────────────

HACKBOT_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "critical": "bold white on red",
    "high": "bold red",
    "medium": "bold yellow",
    "low": "bold blue",
    "title": "bold bright_green",
    "subtitle": "dim",
    "prompt": "bold bright_cyan",
    "agent": "bold magenta",
    "chat": "bold cyan",
    "plan": "bold yellow",
    "tool": "bold green",
    "dim": "dim white",
})

console = Console(theme=HACKBOT_THEME)

# ── Banner ───────────────────────────────────────────────────────────────────

BANNER = r"""
[bold bright_green]
  ██╗  ██╗ █████╗  ██████╗██╗  ██╗██████╗  ██████╗ ████████╗
  ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝
  ███████║███████║██║     █████╔╝ ██████╔╝██║   ██║   ██║
  ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══██╗██║   ██║   ██║
  ██║  ██║██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝   ██║
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝
[/]
[bold bright_cyan]  AI Cybersecurity Assistant[/] [dim]v{version}[/]
[dim]  ─────────────────────────────────────────────[/]
[dim]  Developed by[/] [bold bright_white]Yashab Alam[/]
[dim]  GitHub:[/]   [dim underline]https://github.com/yashab-cyber[/]
[dim]  LinkedIn:[/] [dim underline]https://www.linkedin.com/in/yashab-alam[/]
[dim]  Email:[/]    [dim]yashabalam707@gmail.com | yashabalam9@gmail.com[/]
[dim]  ─────────────────────────────────────────────[/]
[bold bright_red]  ❤️  Support HackBot →[/] [dim underline]https://github.com/yashab-cyber/hackbot/blob/main/DONATE.md[/]
""".replace("{version}", __version__)

BANNER_SMALL = (
    f"[bold bright_green]⚡ HackBot[/] [dim]v{__version__}[/] "
    "[dim]|[/] [bold bright_cyan]AI Cybersecurity Assistant[/] "
    "[dim]|[/] [dim]by Yashab Alam[/]"
)


def show_banner(small: bool = False) -> None:
    """Display the HackBot banner."""
    if small:
        console.print(BANNER_SMALL)
    else:
        console.print(BANNER)


# ── Status & Info ────────────────────────────────────────────────────────────

def show_mode(mode: str) -> None:
    """Display current mode indicator."""
    modes = {
        "chat": ("[chat]💬 Chat Mode[/]", "Interactive cybersecurity Q&A"),
        "agent": ("[agent]🤖 Agent Mode[/]", "Autonomous security testing"),
        "plan": ("[plan]📋 Planning Mode[/]", "Assessment planning & methodology"),
    }
    title, desc = modes.get(mode, ("[info]Unknown Mode[/]", ""))
    console.print(f"\n{title} — [dim]{desc}[/]\n")


def show_config_status(config: Dict[str, Any]) -> None:
    """Display configuration status."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Provider", config.get("provider", "N/A"))
    table.add_row("Model", config.get("model", "N/A"))
    table.add_row("API Key", "✅ Set" if config.get("api_key") else "❌ Not set")
    table.add_row("Safe Mode", "🛡️ Enabled" if config.get("safe_mode") else "⚠️  Disabled")
    table.add_row("Platform", platform.system())

    console.print(Panel(table, title="[title]Configuration[/]", border_style="green"))


def show_tools_status(tools: Dict[str, Optional[str]]) -> None:
    """Display which security tools are available."""
    table = Table(title="Security Tools", show_lines=False)
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    table.add_column("Path", style="dim")

    installed = 0
    for tool, path in sorted(tools.items()):
        if path:
            table.add_row(tool, "[success]✅ Installed[/]", path)
            installed += 1
        else:
            table.add_row(tool, "[dim]❌ Not found[/]", "—")

    console.print(table)
    console.print(
        f"\n[dim]{installed}/{len(tools)} tools available[/]\n"
    )


# ── Messages ─────────────────────────────────────────────────────────────────

def print_user(text: str) -> None:
    """Print user message."""
    console.print(f"\n[bold bright_white]You:[/] {text}")


def print_assistant(text: str, mode: str = "chat") -> None:
    """Print assistant response with markdown rendering."""
    style_map = {"chat": "chat", "agent": "agent", "plan": "plan"}
    style = style_map.get(mode, "chat")
    console.print(f"\n[{style}]HackBot:[/]")
    try:
        md = Markdown(text)
        console.print(md)
    except Exception:
        console.print(text)


def print_streaming_token(token: str) -> None:
    """Print a single streaming token (no newline)."""
    console.print(token, end="", highlight=False)


def print_info(text: str) -> None:
    console.print(f"[info]ℹ {text}[/]")


def print_success(text: str) -> None:
    console.print(f"[success]✅ {text}[/]")


def print_warning(text: str) -> None:
    console.print(f"[warning]⚠️  {text}[/]")


def print_error(text: str) -> None:
    console.print(f"[error]❌ {text}[/]")


# ── Agent-Specific ───────────────────────────────────────────────────────────

def print_tool_execution(tool: str, command: str, explanation: str = "") -> None:
    """Display tool execution with formatting."""
    console.print(f"\n[tool]▶ Executing:[/] [bold]{tool}[/]")
    if explanation:
        console.print(f"  [dim]{explanation}[/]")
    console.print(Syntax(command, "bash", theme="monokai", line_numbers=False))


def print_tool_result(
    tool: str, success: bool, duration: float, output: str, return_code: int
) -> None:
    """Display tool execution result."""
    status = "[success]SUCCESS[/]" if success else "[error]FAILED[/]"
    console.print(
        f"\n[tool]◀ {tool}[/] {status} "
        f"[dim](exit={return_code}, {duration:.1f}s)[/]"
    )
    if output.strip():
        # Truncate for display
        lines = output.strip().split("\n")
        if len(lines) > 50:
            display = "\n".join(lines[:50])
            display += f"\n\n... ({len(lines) - 50} more lines)"
        else:
            display = output.strip()
        console.print(Panel(display, border_style="dim", expand=False))


def print_finding(
    title: str, severity: str, description: str = "",
) -> None:
    """Display a security finding."""
    sev_style = {
        "Critical": "critical",
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Info": "info",
    }.get(severity, "info")

    console.print(
        f"\n[{sev_style}]🔍 [{severity}] {title}[/]"
    )
    if description:
        console.print(f"  {description}")


def print_step(step_num: int, description: str) -> None:
    """Display an agent step."""
    console.print(f"\n[agent]Step {step_num}:[/] {description}")


def confirm_action(command: str, reason: str) -> bool:
    """Ask user to confirm a risky action."""
    console.print(f"\n[warning]⚠️  {reason}[/]")
    console.print(f"  Command: [bold]{command}[/]")
    try:
        response = console.input("[prompt]Execute? (y/N): [/]").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


# ── Help ─────────────────────────────────────────────────────────────────────

def show_help() -> None:
    """Display help information."""
    help_text = """
[title]HackBot Commands[/]

[bold]Modes:[/]
  [chat]/chat[/]              Switch to Chat Mode
  [agent]/agent[/] [target]  Switch to Agent Mode with target
  [plan]/plan[/]              Switch to Planning Mode

[bold]Agent Commands:[/]
  [tool]/run[/] <command>     Execute a security tool manually
  [tool]/step[/]              Execute next agent step
  [tool]/findings[/]          Show discovered findings
  [tool]/stop[/]              Stop current assessment

[bold]Session:[/]
  /save              Save current session
  /load              Load a previous session
  /clear             Clear conversation history
  /reset             Reset to fresh state

[bold]Config:[/]
  /config            Show current configuration
  /tools             Show available security tools
  /model <name>      Switch AI model
  /key <api_key>     Set API key
  /nvd-key <key>     Set NVD API key for faster CVE lookups
  /language <lang>   Set response language (e.g. Spanish, Japanese)

[bold]Other:[/]
  /help              Show this help
  /cve               CVE / vulnerability lookup (NVD)
  /cvss <vector>     CVSS v3.1 vector calculator & score breakdown
  /topology          Network topology map & Mermaid graph
  /osint             OSINT reconnaissance
  /attack            MITRE ATT&CK mapping
  /vulndb            Vulnerability database queries
  /compliance        Compliance mapping (PCI-DSS, OWASP, etc.)
  /export            Export findings/report
  /pdf               Generate professional PDF report
  /diff              Compare two assessments (diff report)
  /remediate         Generate fix commands/patches for findings
  /proxy             HTTP proxy / traffic capture
  /plugins           List/manage custom tool plugins
  /campaign          Multi-target campaign management
  /version           Show version info
  /update            Check for updates / self-update
  /donate            Show donation & contact info
  /manual            Open the HackBot user manual
  /telegram          Telegram bot control (start/stop/status/qr)
  /quit              Exit HackBot
"""
    console.print(help_text)


# ── Progress ─────────────────────────────────────────────────────────────────

def create_spinner(text: str = "Thinking...") -> Progress:
    """Create a spinner for long operations."""
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[dim]{task.description}[/]"),
        console=console,
        transient=True,
    )
