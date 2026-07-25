"""Talking to the Deal Floor.

The chat is not a general assistant bolted to the side. It sees the deal file,
the agent roster, and every deliverable produced so far, so questions like
"what did DCF Modeling assume for WACC?" resolve against actual work rather
than being answered from scratch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import catalog, providers
from .orchestrator import Run

SYSTEM = """You are the desk head on an investment banking deal floor, talking \
to the banker running the mandate.

You have 42 specialist agents, each with a named method drawn from its own \
SKILL.md. You can see the deal file extracted from the attached source \
documents, and every deliverable the agents have produced so far.

HOW TO ANSWER
- Answer from the deal file and the delivered work. Quote the figures that are \
actually there.
- When the answer depends on work no agent has done yet, say which agent would \
produce it and what it needs. Do not improvise the deliverable yourself unless \
asked to.
- When the deal file contradicts something you know, the deal file wins — but \
say plainly that you noticed the conflict.
- Never invent a figure. If you are estimating, mark it as an estimate and say \
what you based it on.
- Be brief and numerate. This is a colleague at a desk, not a report."""


@dataclass
class Turn:
    role: str            # "user" | "assistant"
    text: str
    model: str = ""
    citations: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)


def context(run: Run | None, deal_file: str, subject: str) -> str:
    """The standing brief prepended to every conversation."""
    parts = []
    if subject:
        parts.append(f"SUBJECT: {subject}")
    if run:
        done, total = run.progress()
        parts.append(
            f"MANDATE: {run.mandate.name} — {done} of {total} agents have reported."
        )
    if deal_file.strip():
        parts.append("\nDEAL FILE (authoritative):\n" + _clip(deal_file, 8000))

    if run and run.delivered:
        blocks = [
            f"### {catalog.get(r.slug).title} — {catalog.get(r.slug).deliverable}\n"
            f"{_clip(r.text, 1100)}"
            for r in run.delivered[-10:]
        ]
        parts.append("\nDELIVERABLES SO FAR:\n\n" + "\n\n".join(blocks))

    roster = ", ".join(
        f"{a.title} ({a.deliverable})" for a in catalog.agents().values()
    )
    parts.append("\nAGENTS AVAILABLE: " + roster)
    return "\n".join(parts)


def ask(
    question: str,
    *,
    model_key: str,
    history: list[Turn],
    run: Run | None,
    deal_file: str,
    subject: str,
    attachments: list[dict[str, Any]] | None = None,
    web_search: bool = False,
) -> providers.Reply:
    system = SYSTEM + "\n\n---\n\n" + context(run, deal_file, subject)

    prior = [
        {"role": t.role, "content": t.text}
        for t in history[-12:]
        if t.text.strip()
    ]

    content: list[dict[str, Any]] = list(attachments or [])
    content.append({"type": "text", "text": question})

    return providers.complete(
        model_key,
        system,
        content,
        max_tokens=2000,
        web_search=web_search,
        history=prior,
    )


def _clip(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " […]"
