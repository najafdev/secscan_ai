#!/usr/bin/env python3
# SecScan AI core module
"""
SecScan AI Demo Script
Demonstrates SecScan AI capabilities against a test target
"""

import os
import sys
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, ".")

try:
    try:
        from advance_secscan_ai import SecScanAI as SecScanAI, AIEngine, ToolManager, PentestingPhases
    except ImportError:
        from advance_secscan_ai import SecScanAI, AIEngine, ToolManager, PentestingPhases
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError as e:
    print(f"Error importing SecScan AI: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()


def demo_banner():
    """Display demo banner"""
    banner = """
[bold red]
 ██████╗ ███████╗███╗   ███╗ ██████╗ 
 ██╔══██╗██╔════╝████╗ ████║██╔═══██╗
 ██║  ██║█████╗  ██╔████╔██║██║   ██║
 ██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║
 ██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝
 ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝ 
[/bold red]
[bold cyan]    SecScan AI Demonstration[/bold cyan]
[dim]Safe Testing Against Test Targets[/dim]
"""
    console.print(banner)


def demo_ai_engine():
    """Demonstrate AI Engine capabilities"""
    console.print(Panel("[bold blue]AI Engine Demo[/bold blue]"))

    ai = AIEngine()

    # Test AI analysis
    test_data = """
    Nmap scan results:
    22/tcp open ssh OpenSSH 7.4
    80/tcp open http Apache 2.4.29
    443/tcp open https Apache 2.4.29
    3306/tcp open mysql MySQL 5.7.20
    """

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("AI analyzing scan results...", total=None)

        analysis = ai.analyze("Network scan analysis", test_data, "reconnaissance")

        progress.update(task, completed=100)

    console.print("[green]AI Analysis:[/green]")
    console.print(analysis)
    console.print()


def demo_tool_manager():
    """Demonstrate Tool Manager capabilities"""
    console.print(Panel("[bold blue]Tool Manager Demo[/bold blue]"))

    tools = ToolManager()

    # Test tool checking
    test_tools = ["nmap", "curl", "wget"]
    console.print("[yellow]Checking tools availability:[/yellow]")

    for tool in test_tools:
        available = tools.check_tool(tool)
        status = "✅" if available else "❌"
        console.print(f"  {status} {tool}")

    # Test safe command execution
    console.print("\n[yellow]Testing safe command execution:[/yellow]")
    result = tools.run_command("echo 'SecScan AI Demo Test'")

    if result["success"]:
        console.print(f"  ✅ Command output: {result['stdout'].strip()}")
    else:
        console.print(f"  ❌ Command failed: {result['stderr']}")

    console.print()


def demo_reconnaissance_phase():
    """Demonstrate reconnaissance phase"""
    console.print(Panel("[bold blue]Reconnaissance Phase Demo[/bold blue]"))

    # Use a safe test target
    target = "httpbin.org"
    scope = "HTTP testing service"
    auth_key = "DEMO-2024"

    console.print(f"[cyan]Target: {target}[/cyan]")
    console.print(f"[cyan]Scope: {scope}[/cyan]")

    # Initialize components
    ai = AIEngine()
    tools = ToolManager()

    # Create phases instance
    phases = PentestingPhases(ai, tools, target, scope, auth_key)

    console.print(
        "\n[yellow]Running reconnaissance phase (limited for demo)...[/yellow]"
    )

    # Simulate some reconnaissance activities
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # WHOIS lookup
        task1 = progress.add_task("Running WHOIS lookup...", total=None)
        whois_result = tools.run_command(f"whois {target}")
        progress.update(task1, completed=100)

        # Basic nmap scan (very limited)
        task2 = progress.add_task("Running basic port scan...", total=None)
        nmap_result = tools.run_command(f"nmap -p 80,443 {target}")
        progress.update(task2, completed=100)

    # AI analysis of results
    combined_results = f"WHOIS: {whois_result['stdout'][:200]}...\nNMAP: {nmap_result['stdout'][:200]}..."
    ai_analysis = ai.analyze(
        f"Demo reconnaissance of {target}", combined_results, "reconnaissance"
    )

    console.print("\n[green]AI Analysis of Reconnaissance:[/green]")
    console.print(ai_analysis)
    console.print()


def demo_web_dashboard():
    """Demonstrate web dashboard setup"""
    console.print(Panel("[bold blue]Web Dashboard Demo[/bold blue]"))

    console.print("[yellow]Web dashboard features:[/yellow]")
    console.print("  🌐 Browser-based interface")
    console.print("  📊 Real-time scan monitoring")
    console.print("  📁 Report management")
    console.print("  ⚙️  Configuration management")

    console.print("\n[cyan]To start web dashboard:[/cyan]")
    console.print("  ./advance_secscan_ai.py --web")
    console.print("  Then open: http://localhost:5000")
    console.print()


def demo_voice_interface():
    """Demonstrate voice interface"""
    console.print(Panel("[bold blue]Voice Interface Demo[/bold blue]"))

    console.print("[yellow]Voice commands supported:[/yellow]")
    console.print("  🎤 'Start full pentest'")
    console.print("  🎤 'View reports'")
    console.print("  🎤 'Configure AI'")
    console.print("  🎤 'Help'")
    console.print("  🎤 'Exit'")

    console.print("\n[cyan]To start voice mode:[/cyan]")
    console.print("  ./advance_secscan_ai.py --voice")
    console.print()


def demo_reporting():
    """Demonstrate reporting capabilities"""
    console.print(Panel("[bold blue]Reporting System Demo[/bold blue]"))

    # Create a sample report structure
    sample_findings = {
        "high_risk": ["SQL Injection in login form", "Unpatched SSH service"],
        "medium_risk": ["Directory traversal", "Information disclosure"],
        "low_risk": ["Missing security headers", "Verbose error messages"],
    }

    console.print("[yellow]Report formats available:[/yellow]")
    console.print("  📄 Markdown (.md)")
    console.print("  📊 JSON (.json)")
    console.print("  📋 PDF (via pandoc)")
    console.print("  🌐 HTML dashboard")

    console.print("\n[green]Sample findings summary:[/green]")
    for risk_level, findings in sample_findings.items():
        console.print(f"  {risk_level.upper()}: {len(findings)} issues")
        for finding in findings:
            console.print(f"    • {finding}")

    console.print(f"\n[cyan]Reports saved to: /reports/[target]/[/cyan]")
    console.print()


def demo_security_features():
    """Demonstrate security features"""
    console.print(Panel("[bold blue]Security Features Demo[/bold blue]"))

    console.print("[yellow]Built-in security controls:[/yellow]")
    console.print("  🔐 Mandatory authorization key")
    console.print("  ⚠️  Confirmation prompts for exploits")
    console.print("  🚫 No auto-exploitation without approval")
    console.print("  🔒 Sensitive data not logged")
    console.print("  ⏱️  Rate limiting for brute force")
    console.print("  🛡️  Timeout controls for all operations")

    console.print("\n[green]Authorization check example:[/green]")
    console.print("  Target: example.com")
    console.print("  Scope: Web application testing")
    console.print("  Auth Key: ████████████████")
    console.print("  Status: ✅ Authorized for testing")
    console.print()


def main():
    """Main demo function"""
    demo_banner()

    console.print("[bold yellow]Welcome to the SecScan AI demonstration![/bold yellow]")
    console.print("This demo showcases SecScan AI's capabilities in a safe environment.\n")

    demos = [
        ("AI Engine", demo_ai_engine),
        ("Tool Manager", demo_tool_manager),
        ("Reconnaissance Phase", demo_reconnaissance_phase),
        ("Web Dashboard", demo_web_dashboard),
        ("Voice Interface", demo_voice_interface),
        ("Reporting System", demo_reporting),
        ("Security Features", demo_security_features),
    ]

    for demo_name, demo_func in demos:
        try:
            demo_func()
            time.sleep(2)  # Brief pause between demos
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted by user[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error in {demo_name} demo: {e}[/red]")

    console.print("[bold green]Demo completed![/bold green]")
    console.print("\n[cyan]Ready to use SecScan AI? Run:[/cyan]")
    console.print("  ./advance_secscan_ai.py                  # Interactive mode")
    console.print("  ./advance_secscan_ai.py --web            # Web dashboard")
    console.print("  ./advance_secscan_ai.py --voice          # Voice commands")
    console.print("  ./advance_secscan_ai.py --help           # Show all options")


if __name__ == "__main__":
    main()


# 🔗 Connect with Developer & Founder
# Yashab Alam
# Instagram: https://www.instagram.com/yashabcyber
# X (Twitter): https://x.com/_gh0st0fs0l
# LinkedIn: https://www.linkedin.com/in/yashab-alam
# Threads: https://www.threads.com/@yashabcyber
# Discord: https://discord.gg/eXPjM3Hxwb
# Email: yashabalam9@gmail.com | yashabalam707@gmail.com
