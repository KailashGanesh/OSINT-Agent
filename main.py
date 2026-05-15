import argparse
import asyncio
import os
import sys

from tui import (
    console,
    show_banner,
    display_tool_calls,
    display_report,
    spinner_context,
)

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")

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


if __name__ == "__main__":
    asyncio.run(main())
