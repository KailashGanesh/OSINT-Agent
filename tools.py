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

