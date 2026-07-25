"""Running a mandate.

Stages run in order; the agents inside a stage run at once. Each agent sees
the deal file plus the deliverables from earlier stages, so the chain
accumulates rather than restarting cold at every node.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from . import catalog, providers
from .catalog import Agent, Mandate

MAX_PARALLEL = 4


@dataclass
class Result:
    slug: str
    text: str = ""
    error: str = ""
    model: str = ""
    citations: list[str] = field(default_factory=list)
    tokens: int = 0
    seconds: float = 0.0
    at: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.error


@dataclass
class RunConfig:
    subject: str
    mandate_id: str
    analysis_model: str = "opus-4.8"
    research_model: str = "sonar-pro"
    deal_file: str = ""
    notes: str = ""
    web_search: bool = True

    def model_for(self, agent: Agent) -> str:
        """Research agents go to the search vendor; the rest reason locally."""
        return self.research_model if agent.researches else self.analysis_model


@dataclass
class Run:
    config: RunConfig
    results: dict[str, Result] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    stage: int = 0
    started: float = field(default_factory=time.time)

    @property
    def mandate(self) -> Mandate:
        return catalog.mandates()[self.config.mandate_id]

    @property
    def finished(self) -> bool:
        return self.stage >= len(self.mandate.stages)

    @property
    def delivered(self) -> list[Result]:
        return [self.results[s] for s in self.order if self.results[s].ok]

    def status(self, slug: str) -> str:
        r = self.results.get(slug)
        if r is None:
            return "idle"
        return "done" if r.ok else "failed"

    def progress(self) -> tuple[int, int]:
        agents = self.mandate.agents
        done = sum(1 for s in agents if s in self.results)
        return done, len(agents)

    def upstream(self, slug: str) -> list[tuple[Agent, str]]:
        return [
            (catalog.get(s), self.results[s].text)
            for s in self.order
            if s != slug and self.results[s].ok
        ]

    def cost_tokens(self) -> int:
        return sum(r.tokens for r in self.results.values())


def run_agent(run: Run, slug: str) -> Result:
    """One agent, one call, one deliverable."""
    agent = catalog.get(slug)
    cfg = run.config
    model_key = cfg.model_for(agent)
    started = time.time()

    system = catalog.system_prompt(agent)
    user = catalog.user_prompt(
        agent,
        mandate=run.mandate,
        subject=cfg.subject,
        deal_file=cfg.deal_file,
        notes=cfg.notes,
        upstream=run.upstream(slug),
    )

    # Claude only reaches the web when asked; Perplexity always does.
    wants_web = (
        cfg.web_search
        and agent.researches
        and not providers.BY_KEY[model_key].searches
    )

    try:
        reply = providers.complete(
            model_key, system, user, max_tokens=1400, web_search=wants_web
        )
        return Result(
            slug=slug,
            text=reply.text,
            model=reply.model,
            citations=reply.citations,
            tokens=reply.tokens,
            seconds=time.time() - started,
            at=time.strftime("%H:%M:%S"),
        )
    except providers.ProviderError as exc:
        return Result(
            slug=slug,
            error=str(exc),
            model=providers.BY_KEY[model_key].label,
            seconds=time.time() - started,
            at=time.strftime("%H:%M:%S"),
        )


def run_stage(
    run: Run,
    index: int,
    on_result: Callable[[Result], None] | None = None,
) -> list[Result]:
    """Every unfinished agent in one stage, in parallel."""
    _, slugs = run.mandate.stages[index]
    todo = [s for s in slugs if s not in run.results]
    if not todo:
        return []

    out: list[Result] = []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(todo))) as pool:
        for result in pool.map(lambda s: run_agent(run, s), todo):
            run.results[result.slug] = result
            if result.ok:
                run.order.append(result.slug)
            out.append(result)
            if on_result:
                on_result(result)
    return out


def retry(run: Run, slug: str) -> Result:
    run.results.pop(slug, None)
    if slug in run.order:
        run.order.remove(slug)
    result = run_agent(run, slug)
    run.results[slug] = result
    if result.ok:
        run.order.append(slug)
    return result


def memo(run: Run, sources: list[str] | None = None) -> str:
    """Every deliverable in stage order, as one markdown document."""
    cfg = run.config
    lines = [
        f"# {run.mandate.name} — {cfg.subject}",
        "",
        f"*{len(run.delivered)} agent deliverables, produced on the Deal Floor.*",
        "",
    ]
    if sources:
        lines += [f"**Sources.** {', '.join(sources)}", ""]
    if cfg.notes.strip():
        lines += [f"**Situation.** {cfg.notes.strip()}", ""]
    lines += [
        f"**Models.** {providers.BY_KEY[cfg.analysis_model].label} for analysis, "
        f"{providers.BY_KEY[cfg.research_model].label} for research.",
        "", "---", "",
    ]
    if cfg.deal_file.strip():
        lines += ["## Deal file", "", cfg.deal_file.strip(), "", "---", ""]

    for label, slugs in run.mandate.stages:
        staged = [s for s in slugs if s in run.results and run.results[s].ok]
        if not staged:
            continue
        lines += [f"## {label}", ""]
        for slug in staged:
            agent, result = catalog.get(slug), run.results[slug]
            lines += [f"### {agent.title} — {agent.deliverable}", "", result.text, ""]
            if result.citations:
                lines.append("**Sources.** " + " · ".join(result.citations[:8]))
                lines.append("")
        lines += ["---", ""]

    failed = [s for s, r in run.results.items() if not r.ok]
    if failed:
        lines += ["## Did not complete", ""]
        lines += [
            f"- **{catalog.get(s).title}** — {run.results[s].error}" for s in failed
        ]
        lines.append("")
    return "\n".join(lines)
