import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any


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

