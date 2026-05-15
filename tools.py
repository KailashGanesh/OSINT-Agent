from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

TOOL_REGISTRY: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    async def execute(self, **kwargs: Any) -> str:
        raise NotImplementedError


def register(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str],
):
    def decorator(tool_cls: type[Tool]) -> type[Tool]:
        instance = tool_cls()
        instance.name = name
        instance.description = description
        instance.parameters = parameters
        instance.required = required
        TOOL_REGISTRY[name] = instance
        return tool_cls

    return decorator


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": t.parameters,
                    "required": t.required,
                },
            },
        }
        for t in TOOL_REGISTRY.values()
    ]


def _clean_html(raw: str) -> str:
    for tag in ("script", "style"):
        raw = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"&[a-z]+;", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _resolve_tool(name: str) -> str | None:
    """Return the full path to a CLI tool, preferring the venv copy."""
    venv_bin = os.path.join(os.path.dirname(sys.executable), name)
    if os.path.isfile(venv_bin) and os.access(venv_bin, os.X_OK):
        return venv_bin
    return shutil.which(name)


async def _run_cli_tool(
    tool_name: str,
    pip_pkg: str,
    cli_args: list[str],
    timeout: int,
    no_results_msg: str,
) -> str:
    path = _resolve_tool(tool_name)
    if not path:
        return (
            f"{tool_name} is not installed. "
            f"Install it with: pip install {pip_pkg}\n"
            "Then ensure it is on your PATH."
        )
    try:
        proc = subprocess.run(
            [path, *cli_args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout.strip()
        return output if output else no_results_msg
    except subprocess.TimeoutExpired:
        return f"{tool_name} timed out after {timeout} seconds."
    except Exception as exc:
        return f"{tool_name} error: {exc}"


# ---------------------------------------------------------------------------
# Registered Tools
# ---------------------------------------------------------------------------


@register(
    "search_username",
    "Scan 300+ social platforms for a given username using Sherlock. "
    "Returns a list of sites where the username was found.",
    {
        "username": {
            "type": "string",
            "description": "The username to search for across platforms.",
        },
    },
    ["username"],
)
class SearchUsername(Tool):
    async def execute(self, username: str) -> str:
        return await _run_cli_tool(
            "sherlock",
            "sherlock-project",
            [username, "--print-found", "--timeout", "10", "--local"],
            timeout=90,
            no_results_msg=f'No accounts found for username "{username}".',
        )


@register(
    "harvest_info",
    "Gather emails, subdomains, and names from public sources "
    "using theHarvester. Provide a domain or a full name as the target.",
    {
        "target": {
            "type": "string",
            "description": "Domain (e.g. example.com) or full name to search.",
        },
        "source": {
            "type": "string",
            "description": "Data source: linkedin, google, bing, etc. Default: 'all'.",
        },
    },
    ["target"],
)
class HarvestInfo(Tool):
    async def execute(self, target: str, source: str = "all") -> str:
        result = await _run_cli_tool(
            "theHarvester",
            "theHarvester",
            ["-d", target, "-b", source, "-f", "/dev/null"],
            timeout=60,
            no_results_msg=f"No results for target '{target}'.",
        )
        return result[:4000]


@register(
    "check_email_registration",
    "Check if an email address is registered on various online services "
    "using Holehe. Returns which sites have accounts for that email.",
    {
        "email": {
            "type": "string",
            "description": "The email address to check.",
        },
    },
    ["email"],
)
class CheckEmailRegistration(Tool):
    async def execute(self, email: str) -> str:
        return await _run_cli_tool(
            "holehe",
            "holehe",
            [email, "--only-used"],
            timeout=60,
            no_results_msg=f'No registrations found for "{email}".',
        )


@register(
    "search_web",
    "Perform a DuckDuckGo web search and return titles, URLs, and snippets "
    "for the top results. Use this to find public information about "
    "a person, organisation, or topic.",
    {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
    },
    ["query"],
)
class SearchWeb(Tool):
    async def execute(self, query: str) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            return (
                "ddgs is not installed. "
                "Install it with: pip install ddgs\n"
                "Then ensure it is on your PATH."
            )

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))
        except Exception as exc:
            return f"DuckDuckGo search failed: {exc}"

        if not results:
            return "No search results found."

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            href = r.get("href", "")
            body = r.get("body", "")
            lines.append(f"[{i}] {title}\n    {href}\n    {body}")
        return "\n".join(lines)


@register(
    "fetch_url",
    "Fetch and extract the readable text content of any web page. "
    "Use this after search_web to read detailed information from a URL.",
    {
        "url": {
            "type": "string",
            "description": "The full URL to fetch and extract text from.",
        },
    },
    ["url"],
)
class FetchURL(Tool):
    async def execute(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
            text = _clean_html(resp.text)
            if len(text) > 6000:
                text = text[:6000] + "\n\n[Content truncated at 6000 characters]"
            return text if text.strip() else "(Page contained no readable text)"
        except httpx.HTTPStatusError as exc:
            return f"HTTP {exc.response.status_code} when fetching {url}"
        except Exception as exc:
            return f"Fetch error for {url}: {exc}"


@register(
    "check_email_breaches",
    "Check if an email address appears in known data breaches via the "
    "Have I Been Pwned API. Requires a HIBP API key in HIBP_API_KEY env var.",
    {
        "email": {
            "type": "string",
            "description": "The email address to check for breaches.",
        },
    },
    ["email"],
)
class CheckEmailBreaches(Tool):
    HIBP_API = "https://haveibeenpwned.com/api/v3/breachedaccount/"

    async def execute(self, email: str) -> str:
        api_key = os.getenv("HIBP_API_KEY", "")
        if not api_key:
            return "HIBP_API_KEY not set. Get a free key at https://haveibeenpwned.com/API/Key"

        headers = {
            "hibp-api-key": api_key,
            "user-agent": "osint-agent",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.HIBP_API}{email}",
                    headers=headers,
                )
                if resp.status_code == 404:
                    return f'Email "{email}" was not found in any known breaches. (Good news!)'
                resp.raise_for_status()
                breaches = resp.json()
        except httpx.HTTPStatusError as exc:
            return f"HIBP API error: HTTP {exc.response.status_code}"
        except Exception as exc:
            return f"HIBP API error: {exc}"

        lines = [f'Email "{email}" found in {len(breaches)} breach(es):']
        for b in breaches:
            name = b.get("Name", "Unknown")
            domain = b.get("Domain", "")
            date = b.get("BreachDate", "")
            desc = b.get("Description", "")
            lines.append(
                f"  - {name} ({domain}) — Breach date: {date}\n"
                f"    {desc[:200]}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers called by agent.py
# ---------------------------------------------------------------------------

def get_tool(name: str) -> Tool | None:
    return TOOL_REGISTRY.get(name)
