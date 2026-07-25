"""The 42 agents, the mandates that chain them, and the prompts they run.

Every agent is a SKILL.md file under skills/. data/agents.json is the parsed
form of those files — regenerate it with `python -m dealfloor.build` after
editing any skill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "agents.json"
SKILLS = ROOT / "skills"

# Agents whose method is fundamentally "go and find out what is true right
# now". These default to a live-search model; everything else reasons over the
# deal file and needs no web access.
RESEARCH_AGENTS = frozenset({
    "market-intelligence", "industry-analysis", "company-research",
    "comparable-analysis", "precedent-transactions", "buyer-targeting",
    "investor-targeting", "debt-sourcing", "equity-sourcing",
})


@dataclass(frozen=True)
class Step:
    head: str
    detail: str


@dataclass(frozen=True)
class Agent:
    slug: str
    title: str
    category: str
    category_name: str
    colour: str
    description: str
    when: str
    does: str
    steps: tuple[Step, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    example: str
    deliverable: str

    @property
    def researches(self) -> bool:
        return self.slug in RESEARCH_AGENTS

    @property
    def skill_path(self) -> Path:
        return SKILLS / self.slug / "SKILL.md"


@dataclass(frozen=True)
class Mandate:
    id: str
    name: str
    subtitle: str
    stages: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def agents(self) -> list[str]:
        return [s for _, slugs in self.stages for s in slugs]


@dataclass(frozen=True)
class Category:
    number: str
    name: str
    colour: str
    slugs: tuple[str, ...]


@lru_cache(maxsize=1)
def _raw() -> dict:
    if not DATA.exists():
        raise FileNotFoundError(
            f"{DATA} is missing. Run `python -m dealfloor.build` to generate it "
            "from the skills/ folder."
        )
    return json.loads(DATA.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def agents() -> dict[str, Agent]:
    out = {}
    for slug, a in _raw()["agents"].items():
        out[slug] = Agent(
            slug=slug,
            title=a["title"],
            category=a["cat"],
            category_name=a["catName"],
            colour=a["color"],
            description=a["desc"],
            when=a["when"],
            does=a["does"],
            steps=tuple(Step(s["h"], s["d"]) for s in a["steps"]),
            inputs=tuple(a["inputs"]),
            outputs=tuple(a["outputs"]),
            example=a["example"],
            deliverable=a["deliverable"],
        )
    return out


@lru_cache(maxsize=1)
def mandates() -> dict[str, Mandate]:
    return {
        m["id"]: Mandate(
            id=m["id"],
            name=m["name"],
            subtitle=m["sub"],
            stages=tuple((label, tuple(slugs)) for label, slugs in m["stages"]),
        )
        for m in _raw()["mandates"]
    }


@lru_cache(maxsize=1)
def categories() -> list[Category]:
    return [
        Category(c["n"], c["name"], c["color"], tuple(c["slugs"]))
        for c in _raw()["cats"]
    ]


@lru_cache(maxsize=1)
def standing_desk() -> tuple[str, ...]:
    """PMO agents that run across a whole mandate rather than at one stage."""
    return tuple(_raw()["standing"])


def get(slug: str) -> Agent:
    return agents()[slug]


def search(query: str) -> list[Agent]:
    """Substring match across everything an agent says about itself."""
    q = query.lower().strip()
    if not q:
        return list(agents().values())
    hits = []
    for a in agents().values():
        haystack = " ".join([
            a.slug, a.title, a.description, a.when, a.does, a.deliverable,
            " ".join(s.head + " " + s.detail for s in a.steps),
            " ".join(a.inputs), " ".join(a.outputs),
        ]).lower()
        if q in haystack:
            hits.append(a)
    return hits


# ── prompts ──────────────────────────────────────────────────────────────

def system_prompt(agent: Agent) -> str:
    """The agent's own SKILL.md method, turned into its operating instruction."""
    steps = "\n".join(
        f"{i:02d}. {s.head} {s.detail}".rstrip()
        for i, s in enumerate(agent.steps, 1)
    )
    outputs = "\n".join(f"- {o}" for o in agent.outputs)
    return f"""You are the {agent.title} agent on an investment banking deal team. \
You run one named method and return one deliverable.

METHOD — follow every step in order:
{steps}

OUTPUT FORMAT — return exactly this and nothing else:
{outputs}

RULES
- The deal file is authoritative. Where anything you know or find conflicts \
with it, the deal file wins.
- Use the figures you are given. Where a figure you need is absent, state the \
assumption inline in a few words and move on. Never present an invented figure \
as fact — mark estimates as estimates.
- Be concrete and numerate. This is a working desk output, not an essay.
- Do not restate the method or preface the work. Lead with the output.
- Under 500 words. Short headers, tight bullets."""


def user_prompt(
    agent: Agent,
    *,
    mandate: Mandate,
    subject: str,
    deal_file: str = "",
    notes: str = "",
    upstream: list[tuple[Agent, str]] | None = None,
) -> str:
    parts = [f"MANDATE: {mandate.name}", f"SUBJECT: {subject}"]

    if deal_file.strip():
        parts.append(
            "\nDEAL FILE — extracted from the source documents attached to this "
            "mandate. Authoritative.\n\n" + _clip(deal_file, 9000)
        )
    if notes.strip():
        parts.append("\nADDITIONAL NOTES FROM THE DEAL TEAM:\n" + notes.strip())
    if not deal_file.strip() and not notes.strip():
        parts.append(
            "\nNo documents or notes supplied — work from what you can "
            "establish and flag every gap."
        )
    if upstream:
        blocks = "\n\n".join(
            f"### {up.title} — {up.deliverable}\n{_clip(text, 900)}"
            for up, text in upstream[-6:]
        )
        parts.append("\nUPSTREAM WORK ALREADY DELIVERED ON THIS DEAL:\n\n" + blocks)

    # Left as written — lowercasing mangles DCF, WACC, CIM, NDA, Q&A, QC.
    parts.append(f"\nTASK: Produce the {agent.deliverable} for {subject}.")
    return "\n".join(parts)


def _clip(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " […]"
