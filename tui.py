from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel

from agent import ToolCallRecord
from report import format_for_terminal

console = Console()


def show_banner() -> None:
    banner = """
 ██████╗ ███████╗██╗███╗   ██╗████████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║   ██║███████╗██║██╔██╗ ██║   ██║       ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
██║   ██║╚════██║██║██║╚██╗██║   ██║       ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
╚██████╔╝███████║██║██║ ╚████║   ██║       ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
 ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝       ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝
"""
    console.print(banner, style="bold cyan")
    console.print("  Open-Source Intelligence Agent", style="dim italic")
    console.print()



def display_tool_calls(records: list[ToolCallRecord], verbose: bool) -> None:
    if not verbose:
        return

    console.print("\n[bold]Tool Call Log[/bold]")
    console.print("─" * 60)
    for i, r in enumerate(records, 1):
        console.print(f"\n[bold cyan]#{i} {r.name}[/bold cyan]")
        console.print(f"  Arguments: {json.dumps(r.arguments)}")
        preview = r.result[:300].replace("\n", "\n  ")
        console.print(f"  Result:\n  {preview}")
        if len(r.result) > 300:
            console.print("  [dim]... (truncated)[/dim]")


def display_report(report: str, records: list[ToolCallRecord]) -> None:
    console.print()
    formatted = format_for_terminal(report)
    console.print(Panel(formatted, title="OSINT Report", border_style="green"))

    console.print(
        f"\n[dim]Investigation completed — {len(records)} tool calls made.[/dim]"
    )


def spinner_context(message: str = "Agent is working"):
    return console.status(f"[bold green]{message}...[/bold green]", spinner="dots")
