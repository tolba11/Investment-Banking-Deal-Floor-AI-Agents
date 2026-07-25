# Contributing

## The interesting part is the skills

Each of the 42 agents is `skills/<slug>/SKILL.md`. Its method becomes the
agent's system prompt verbatim. Improving an agent means editing prose, not
code:

```bash
vim skills/dcf-modeling/SKILL.md
python -m dealfloor.build      # refresh data/agents.json
pytest -q
```

A skill needs six sections: `When to use`, `What it does`, `Method` (numbered),
`Inputs` (bulleted), `Output format` (bulleted), `Example`. The parser expects
that shape.

## Adding an agent

1. Create `skills/<slug>/SKILL.md` with those six sections.
2. Add it to `data/agents.json` under `agents`, and to a category in `cats`.
3. Add it to at least one mandate's stages.
4. If it needs live web data, add the slug to `RESEARCH_AGENTS` in
   `dealfloor/catalog.py`.
5. `pytest -q` — the suite checks every agent has a SKILL.md, every mandate
   references real agents, and the categories still partition the roster.

## Adding a provider

`dealfloor/providers.py` is the only file that talks to the outside. Add a
`Model` entry and a `_yourvendor()` function returning a `Reply`. Nothing else
should need to change.

## Style

- No network calls outside `providers.py`.
- Errors reach the operator with the vendor's message intact — never swallowed.
- Tests stub `providers.complete` and run without keys.
