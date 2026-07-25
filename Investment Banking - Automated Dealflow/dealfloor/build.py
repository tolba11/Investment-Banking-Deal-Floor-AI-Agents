"""Regenerate data/agents.json from the skills/ folder.

Run after editing any SKILL.md:

    python -m dealfloor.build
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DATA = ROOT / "data" / "agents.json"


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
    desc = ""
    if fm:
        m = re.search(r"description:\s*(.*)", fm.group(1))
        desc = m.group(1).strip() if m else ""
        text = text[fm.end():]

    sections: dict[str, str] = {}
    for part in re.split(r"\n## ", text)[1:]:
        head, _, rest = part.partition("\n")
        sections[head.strip()] = rest.strip()

    steps = []
    for raw in re.findall(r"^\d+\.\s+(.+)$", sections.get("Method", ""), re.M):
        head = re.match(r"(.+?[.!?])(\s|$)", raw.strip())
        h = head.group(1).strip() if head else raw.strip()
        steps.append({"h": h, "d": raw[len(h):].strip()})

    return {
        "desc": desc,
        "when": sections.get("When to use", ""),
        "does": sections.get("What it does", ""),
        "steps": steps,
        "inputs": re.findall(r"^-\s+(.+)$", sections.get("Inputs", ""), re.M),
        "outputs": re.findall(r"^-\s+(.+)$", sections.get("Output format", ""), re.M),
        "example": sections.get("Example", ""),
    }


def main() -> None:
    if not DATA.exists():
        raise SystemExit(
            f"{DATA} not found. This script refreshes an existing catalogue's "
            "prose from skills/; it does not invent categories or mandates."
        )

    data = json.loads(DATA.read_text(encoding="utf-8"))
    updated = 0
    for slug, agent in data["agents"].items():
        path = SKILLS / slug / "SKILL.md"
        if not path.exists():
            print(f"  ! {slug}: SKILL.md missing, left as-is")
            continue
        agent.update(parse(path))
        updated += 1

    DATA.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"Refreshed {updated} agents from {SKILLS} into {DATA}")


if __name__ == "__main__":
    main()
