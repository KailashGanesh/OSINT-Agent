from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from tools import tool_schemas, get_tool

SYSTEM_PROMPT = """\
You are a methodical OSINT analyst. Your task is to investigate a person
using only public, legal, and ethical means.

You have a budget of {max_turns} tool calls. Plan your investigation
accordingly so you can produce a final report within this limit.

## Workflow
1. Start with a web search using the person's name, location, and any known socials.
2. For each social handle discovered, run a username search across platforms.
3. For any email addresses found, check breach databases and service registrations.
4. Fetch and read relevant pages for deeper detail.
5. Cross-reference findings across sources.
6. When you have exhausted useful leads or are approaching your call limit,
   produce a final report — do not keep searching indefinitely.

## Rules
- Only use the tools provided. Do not invent facts.
- Cite the source (URL or tool name) for every finding.
- Mention when a tool returns no results — be honest about gaps.
- Never guess or fabricate information.
- You WILL produce a final report after your last tool call, even if some
  leads remain unexplored.

## Final Report Format
When you are done gathering information, output a structured report using
this exact Markdown template:

---
## OSINT Report — [Full Name]

### Identity Summary
- **Name:** [Full Name]
- **Age / DOB:** [if known]
- **Location:** [city, country]
- **Known Social Handles:** [list]

### Online Presence
[List each social / professional profile found with the platform name and URL.
Include a one-line summary of what the profile reveals.]

### Email & Breach Exposure
[For each email found: list breach names, dates, and data exposed.
If HIBP returned nothing, note "No known breaches" as a positive finding.]

### Associated Accounts
[Cross-reference: which usernames appear on which platforms.
Mention patterns — e.g. same handle reused across sites.]

### Risk Assessment
[Assess the subject's digital footprint:
- How exposed are they?
- Do they reuse credentials across platforms?
- Are there any concerning findings in breach data?
Rate overall risk as Low / Medium / High with a brief justification.]

### Sources
[List every URL and tool output used to compile this report.]
---

If the person cannot be found or minimal data exists, produce the same
template with "No data found" for each section — do not fabricate.
"""


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class AgentResult:
    report: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


async def run(
    client: AsyncOpenAI,
    model: str,
    subject: dict[str, str],
    max_turns: int = 15,
) -> AgentResult:
    user_content = "Investigate this person:\n"
    for key, value in subject.items():
        user_content += f"- {key}: {value}\n"
    user_content += (
        "\nBe systematic. Use every relevant tool at your disposal. "
        "End with the structured report."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(max_turns=max_turns)},
        {"role": "user", "content": user_content},
    ]

    records: list[ToolCallRecord] = []

    for turn in range(max_turns):
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_schemas(),
            tool_choice="auto",
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            assistant_msg = choice.message
            messages.append(assistant_msg.model_dump(exclude_none=True))

            for tc in assistant_msg.tool_calls or []:
                tool = get_tool(tc.function.name)
                if tool is None:
                    result = f"Unknown tool: {tc.function.name}"
                    args = {}
                else:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        result = await tool.execute(**args)
                    except Exception as exc:
                        result = f"Tool error: {exc}"

                records.append(
                    ToolCallRecord(
                        name=tc.function.name,
                        arguments=args,
                        result=result,
                    )
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        else:
            report = choice.message.content or ""
            return AgentResult(report=report, tool_calls=records)

    messages.append({
        "role": "user",
        "content": (
            f"You have used all {max_turns} available tool calls. "
            "Do not request any more tools. Produce the final structured "
            "report now based on everything you have gathered."
        ),
    })
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        tool_choice="none",
    )
    report = response.choices[0].message.content or ""
    return AgentResult(report=report, tool_calls=records)
