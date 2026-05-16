from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agent import run
from report import save_report
from tui import (
    console,
    show_banner,
    display_tool_calls,
    display_report,
    spinner_context,
)

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
LLM_BASE = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OSINT Agent — gather public info on a person using LLM-driven tools.",
    )
    parser.add_argument("--name", help="Full name of the person to investigate.")
    parser.add_argument("--age", help="Approximate age of the person.")
    parser.add_argument("--location", help="City or country the person is based in.")
    parser.add_argument("--socials", help="Known social handles, comma-separated.")
    parser.add_argument("--email", help="Known email address of the person.")
    parser.add_argument("--phone", help="Known phone number of the person.")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed tool call output."
    )
    parser.add_argument(
        "--save", metavar="PATH", default="report.md", help="Save the report to a file."
    )
    parser.add_argument(
        "--model", default=MODEL, help=f"Model to use (default: {MODEL})."
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if not os.getenv("LLM_API_KEY"):
        console.print("[bold red]LLM_API_KEY not set in .env[/bold red]")
        console.print("[dim]Get your key at https://opencode.ai/auth[/dim]")
        sys.exit(1)

    show_banner()

    name = args.name or input("Full name: ").strip()
    age = args.age or input("Approximate age (optional): ").strip()
    location = args.location or input("Location (city/country): ").strip()
    socials = args.socials or input("Known social handles (comma-separated, optional): ").strip()
    email = args.email or input("Known email (optional): ").strip()
    phone = args.phone or input("Known phone number (optional): ").strip()

    if not name and not email:
        console.print("[bold red]At minimum, a name or email is required.[/bold red]")
        sys.exit(1)

    subject: dict[str, str] = {}
    if name:
        subject["Name"] = name
    if age:
        subject["Age"] = age
    if location:
        subject["Location"] = location
    if socials:
        subject["Known Social Handles"] = socials
    if email:
        subject["Email"] = email
    if phone:
        subject["Phone"] = phone

    client = AsyncOpenAI(
        base_url=LLM_BASE,
        api_key=os.getenv("LLM_API_KEY"),
    )

    try:
        with spinner_context("Investigating"):
            result = await run(client, args.model, subject)
    except Exception as exc:
        console.print(f"\n[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    if args.verbose:
        display_tool_calls(result.tool_calls, verbose=True)

    display_report(result.report, result.tool_calls)

    if args.save:
        path = save_report(result.report, args.save)
        console.print(f"\n[dim]Report saved to {path}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
