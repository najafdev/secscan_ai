"""
OpenOS Rich Output Formatter.

Formats AI responses, system health reports, file listings, and error messages
with rich terminal styling using the Rich library.
"""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

OPENOS_THEME = Theme({
    "openos.brand": "bold cyan",
    "openos.success": "bold green",
    "openos.warning": "bold yellow",
    "openos.error": "bold red",
    "openos.info": "dim cyan",
    "openos.action": "bold magenta",
    "openos.prompt": "bold blue",
})

console = Console(theme=OPENOS_THEME)


def print_welcome() -> None:
    """Print the OpenOS welcome banner."""
    banner = Text()
    banner.append("\n ███████╗ █████╗ ██╗\n", style="bold cyan")
    banner.append(" ██╔════╝██╔══██╗██║\n", style="bold cyan")
    banner.append(" ███████╗███████║██║\n", style="bold blue")
    banner.append(" ╚════██║██╔══██║██║\n", style="bold blue")
    banner.append(" ███████║██║  ██║██║\n", style="bold magenta")
    banner.append(" ╚══════╝╚═╝  ╚═╝╚═╝\n", style="bold magenta")
    console.print(banner)
    console.print("  [openos.brand]OpenOS[/] — Your AI Operating System", justify="center")
    console.print("  [openos.info]Type anything in natural language. Type 'exit' to quit.[/]\n")


def print_response(response: str) -> None:
    """Print an AI response with markdown rendering."""
    if not response:
        return
    try:
        md = Markdown(response)
        console.print(md)
    except Exception:
        console.print(response)


def print_action(action: str) -> None:
    """Print a tool action being executed."""
    console.print(f"  [openos.action]⚡ {action}[/]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"  [openos.success]{message}[/]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(Panel(
        f"[openos.error]{message}[/]",
        title="[openos.error]Error[/]",
        border_style="red",
        padding=(0, 1),
    ))


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"  [openos.warning]⚠️  {message}[/]")


def print_confirm(message: str) -> bool:
    """Print a confirmation prompt and return True if user confirms."""
    console.print(Panel(
        message,
        title="[openos.warning]Confirmation Required[/]",
        border_style="yellow",
        padding=(0, 1),
    ))
    try:
        answer = console.input("  [openos.prompt]Proceed? (y/n): [/]").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def print_thinking() -> None:
    """Print a thinking indicator."""
    console.print("  [openos.info]🧠 Thinking...[/]", end="\r")


def clear_thinking() -> None:
    """Clear the thinking indicator."""
    console.print(" " * 40, end="\r")


def print_actions_summary(actions: list[dict]) -> None:
    """Print a summary of tool actions taken."""
    if not actions:
        return
    console.print("\n  [openos.info]Actions taken:[/]")
    for action in actions:
        tool = action.get("tool", "unknown")
        result = action.get("result", {})
        status = "[openos.success]✅[/]" if result.get("success") else "[openos.error]❌[/]"
        console.print(f"    {status} {tool}")
