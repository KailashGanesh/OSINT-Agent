from __future__ import annotations

import re


def extract_sections(report: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_body: list[str] = []

    for line in report.split("\n"):
        m = re.match(r"^###\s+(.+)", line)
        if m:
            if current_heading:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = m.group(1).strip()
            current_body = []
        elif current_heading:
            current_body.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(current_body).strip()

    return sections


def format_for_terminal(report: str) -> str:
    sections = extract_sections(report)
    if not sections:
        return report

    out: list[str] = []
    title = next(
        (k for k in sections if k.lower().startswith("osint report")),
        list(sections.keys())[0] if sections else "OSINT Report",
    )
    body = sections.get(title, "")

    out.append(f"╔{'═' * 58}╗")
    out.append(f"║  {title.center(56)}║")
    out.append(f"╚{'═' * 58}╝")
    if body.strip():
        out.append(body.strip())

    for heading, body in sections.items():
        if heading == title:
            continue
        out.append(f"\n{'─' * 60}")
        out.append(f"  {heading}")
        out.append(f"{'─' * 60}")
        out.append(body.strip())

    return "\n".join(out)


def save_report(report: str, path: str = "report.md") -> str:
    with open(path, "w") as f:
        f.write(report)
    return path
