"""Investment Banking — Deal Floor AI Agents

42 specialist agents, each running the method from its own SKILL.md.

    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from dealfloor import catalog, chat, intake, orchestrator, providers, ui
from dealfloor.orchestrator import Run, RunConfig

st.set_page_config(
    page_title="Investment Banking — Deal Floor AI Agents",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── secrets ──────────────────────────────────────────────────────────────

def load_keys() -> None:
    """Streamlit secrets win, environment is the fallback."""
    for name in ("ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY"):
        try:
            value = st.secrets[name]
        except Exception:  # noqa: BLE001 — no secrets file is a valid setup
            value = None
        if value:
            os.environ[name] = str(value)


def state() -> None:
    ss = st.session_state
    ss.setdefault("sources", [])
    ss.setdefault("deal_file", "")
    ss.setdefault("deal_file_edited", False)
    ss.setdefault("chat", [])
    ss.setdefault("run", None)
    ss.setdefault("auto", False)
    ss.setdefault("subject", "")
    ss.setdefault("notes", "")
    ss.setdefault("seen_files", set())


load_keys()
state()
ui.theme()

HAS_CLAUDE = providers.available("anthropic")
HAS_PPLX = providers.available("perplexity")


# ── sidebar ──────────────────────────────────────────────────────────────

def sidebar() -> RunConfig:
    ss = st.session_state
    with st.sidebar:
        ui.masthead("Deal Floor", "42 AGENTS")
        st.caption("Investment Banking — Deal Floor AI Agents")
        st.caption("Every agent runs a method from its own SKILL.md.")

        if not HAS_CLAUDE and not HAS_PPLX:
            st.error(
                "No API keys found. Add `ANTHROPIC_API_KEY` and optionally "
                "`PERPLEXITY_API_KEY` to `.streamlit/secrets.toml`, then reload."
            )

        st.divider()

        mandates = catalog.mandates()
        ui.eyebrow("Mandate")
        mandate_id = st.selectbox(
            "Mandate",
            list(mandates),
            format_func=lambda k: mandates[k].name,
            label_visibility="collapsed",
        )
        m = mandates[mandate_id]
        st.caption(f"{m.subtitle} — {len(m.agents)} agents across {len(m.stages)} stages.")

        st.divider()
        ui.eyebrow("Source documents")
        uploads = st.file_uploader(
            "Attach the deal documents",
            type=["pdf", "xlsx", "xlsm", "csv", "tsv", "docx", "txt", "md",
                  "json", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        ingest(uploads)

        pending = [s for s in ss.sources if s.ready and not s.digest]
        if ss.sources:
            for s in ss.sources:
                mark = "✕" if s.error else ("✓" if s.digest else "·")
                note = s.error or ("fact base extracted" if s.digest else "not read yet")
                st.markdown(
                    f'<div class="cite">{mark} <b>{s.name}</b> — {note}</div>',
                    unsafe_allow_html=True,
                )
            st.write("")

        st.divider()
        ui.eyebrow("Deal brief")
        ss.subject = st.text_input(
            "Subject",
            value=ss.subject,
            placeholder="Company or deal",
            label_visibility="collapsed",
        )
        ss.notes = st.text_area(
            "Notes",
            value=ss.notes,
            placeholder="Anything the documents don't say — process dynamics, "
                        "seller motivation, constraints.",
            height=90,
            label_visibility="collapsed",
        )

        st.divider()
        ui.eyebrow("Models")
        claude_keys = [m.key for m in providers.ANTHROPIC_MODELS]
        pplx_keys = [m.key for m in providers.PERPLEXITY_MODELS]

        analysis = st.selectbox(
            "Analysis and structuring",
            claude_keys,
            format_func=lambda k: providers.BY_KEY[k].label,
            help="Runs the 33 agents that reason over the deal file.",
        )
        st.caption(providers.BY_KEY[analysis].note)

        research_pool = (pplx_keys if HAS_PPLX else []) + claude_keys
        research = st.selectbox(
            "Research and sourcing",
            research_pool,
            format_func=lambda k: providers.BY_KEY[k].label,
            help="Runs the 9 agents that need live market data.",
        )
        st.caption(providers.BY_KEY[research].note)

        web = st.toggle(
            "Let Claude research agents search the web",
            value=True,
            help="Ignored when a Perplexity model is chosen — those always search.",
        )

        # Intake reads PDFs and screenshots natively, which only Claude does,
        # so this list stays Claude-only regardless of the research vendor.
        intake_model = st.selectbox(
            "Document intake",
            claude_keys,
            index=claude_keys.index("haiku-4.5") if "haiku-4.5" in claude_keys else 0,
            format_func=lambda k: providers.BY_KEY[k].label,
            help="Reads each source document once into the deal file.",
        )

        st.divider()
        run_config = RunConfig(
            subject=ss.subject.strip(),
            mandate_id=mandate_id,
            analysis_model=analysis,
            research_model=research,
            deal_file=ss.deal_file,
            notes=ss.notes.strip(),
            web_search=web,
        )

        if pending:
            if st.button(
                f"Read {len(pending)} document{'s' if len(pending) > 1 else ''}",
                type="primary", use_container_width=True, disabled=not HAS_CLAUDE,
            ):
                read_sources(intake_model)
                st.rerun()

        blocked = not ss.subject.strip() or (not HAS_CLAUDE and not HAS_PPLX)
        c1, c2 = st.columns([3, 2])
        with c1:
            if st.button("▶ Run mandate", type="primary",
                         disabled=blocked or ss.auto, use_container_width=True):
                ss.run = Run(config=run_config)
                ss.auto = True
                st.rerun()
        with c2:
            if st.button("Reset", use_container_width=True):
                ss.run = None
                ss.auto = False
                st.rerun()

        if blocked and not ss.subject.strip():
            st.caption("Name a subject to run.")

        if ss.run:
            done, total = ss.run.progress()
            st.progress(done / total if total else 0.0)
            st.caption(
                f"{done} of {total} agents · stage "
                f"{min(ss.run.stage + 1, len(ss.run.mandate.stages))} of "
                f"{len(ss.run.mandate.stages)} · {ss.run.cost_tokens():,} tokens"
            )
        return run_config


def ingest(uploads) -> None:
    """Read each newly attached file once."""
    if not uploads:
        return
    ss = st.session_state
    for f in uploads:
        token = f"{f.name}:{f.size}"
        if token in ss.seen_files:
            continue
        ss.seen_files.add(token)
        ss.sources.append(intake.read(f.name, f.getvalue()))


def read_sources(model_key: str) -> None:
    ss = st.session_state
    pending = [s for s in ss.sources if s.ready and not s.digest]
    bar = st.sidebar.progress(0.0, text="Reading…")
    for i, src in enumerate(pending, 1):
        bar.progress((i - 1) / len(pending), text=f"Reading {src.name}")
        intake.digest(src, model_key)
        if src.entity and not ss.subject.strip():
            ss.subject = src.entity
    bar.empty()
    if not ss.deal_file_edited:
        ss.deal_file = intake.deal_file(ss.sources)


# ── the floor ────────────────────────────────────────────────────────────

def floor(cfg: RunConfig) -> None:
    ss = st.session_state
    mandate = catalog.mandates()[cfg.mandate_id]
    run: Run | None = ss.run

    st.markdown(f"### {mandate.name}")
    st.caption(mandate.subtitle)

    if run and ss.auto and not run.finished:
        label, _ = mandate.stages[run.stage]
        with st.status(
            f"Stage {run.stage + 1:02d} · {label}", expanded=True
        ) as box:
            for result in orchestrator.run_stage(run, run.stage):
                agent = catalog.get(result.slug)
                if result.ok:
                    st.write(
                        f"✓ **{agent.title}** — {agent.deliverable} "
                        f"· {result.model} · {result.seconds:.1f}s"
                    )
                else:
                    st.write(f"✕ **{agent.title}** — {result.error}")
            box.update(label=f"Stage {run.stage + 1:02d} · {label}", state="complete")
        run.stage += 1
        if run.finished:
            ss.auto = False
        st.rerun()

    if run and run.finished:
        ok = len(run.delivered)
        st.success(f"Mandate complete — {ok} of {len(mandate.agents)} agents delivered.")

    for i, (label, slugs) in enumerate(mandate.stages):
        if run is None:
            cls, mark = "", "idle"
        elif run.stage > i:
            cls = "done"
        elif run.stage == i and ss.auto:
            cls = "live"
        else:
            cls = ""

        nodes = []
        for slug in slugs:
            agent = catalog.get(slug)
            status = run.status(slug) if run else "idle"
            if run and run.stage == i and ss.auto and status == "idle":
                status = "live"
            caption = agent.deliverable
            if run and slug in run.results:
                r = run.results[slug]
                caption = agent.deliverable if r.ok else "failed"
            nodes.append(ui.node(agent, status, caption))

        st.markdown(
            f'<div class="stage {cls}"><h4><em>STAGE {i + 1:02d}</em>{label}</h4>'
            + "".join(nodes)
            + "</div>",
            unsafe_allow_html=True,
        )

    standing = [s for s in catalog.standing_desk() if s not in mandate.agents]
    if standing:
        st.write("")
        ui.eyebrow("Standing desk — not staged in this mandate")
        pills = "".join(
            f'<span class="pill">{catalog.get(s).title}</span>' for s in standing
        )
        st.markdown(pills, unsafe_allow_html=True)


def deliverables() -> None:
    ss = st.session_state
    run: Run | None = ss.run
    if not run or not run.results:
        st.info("Nothing shipped yet. Run a mandate and the deliverables land here.")
        return

    sources = [s.name for s in ss.sources]
    st.download_button(
        "Download the deal memo",
        data=orchestrator.memo(run, sources),
        file_name=f"{(run.config.subject or 'deal').lower().replace(' ', '-')}-memo.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.write("")

    for label, slugs in run.mandate.stages:
        staged = [s for s in slugs if s in run.results]
        if not staged:
            continue
        ui.eyebrow(label)
        for slug in staged:
            agent, r = catalog.get(slug), run.results[slug]
            icon = "✓" if r.ok else "✕"
            with st.expander(f"{icon}  {agent.title} — {agent.deliverable}", expanded=False):
                if r.ok:
                    st.markdown(r.text)
                    ui.citations(r.citations)
                    st.caption(f"{r.model} · {r.tokens:,} tokens · {r.seconds:.1f}s")
                else:
                    st.error(r.error)
                if st.button("Run this agent again", key=f"retry-{slug}"):
                    with st.spinner(f"{agent.title}…"):
                        orchestrator.retry(run, slug)
                    st.rerun()
        st.write("")


def deal_file_view() -> None:
    ss = st.session_state
    if not ss.sources:
        st.info(
            "No documents attached. Drop the annual report, the CIQ pull, the "
            "model, or a PitchBook screenshot into the sidebar — everything the "
            "agents assert will be traceable to what you put there."
        )
        return

    read = sum(1 for s in ss.sources if s.digest)
    st.caption(
        f"The fact base every agent works from, extracted from {read} of "
        f"{len(ss.sources)} documents. Edit freely — corrections here reach all 42."
    )
    edited = st.text_area(
        "Deal file",
        value=ss.deal_file,
        height=440,
        label_visibility="collapsed",
        placeholder="Read the documents to populate this, or type the fact base yourself.",
    )
    if edited != ss.deal_file:
        ss.deal_file = edited
        ss.deal_file_edited = True

    failed = [s for s in ss.sources if s.error]
    if failed:
        st.warning("Could not read: " + ", ".join(f"{s.name} ({s.error})" for s in failed))


def library() -> None:
    query = st.text_input(
        "Search", placeholder="Search 42 agents — try WACC, BATNA, RACI, critical path",
        label_visibility="collapsed",
    )
    hits = catalog.search(query)
    st.caption(f"{len(hits)} of 42 agents")

    by_cat: dict[str, list] = {}
    for a in hits:
        by_cat.setdefault(a.category, []).append(a)

    for cat in catalog.categories():
        group = by_cat.get(cat.number)
        if not group:
            continue
        ui.eyebrow(f"{cat.number} · {cat.name}")
        for a in group:
            with st.expander(f"{a.title} — {a.deliverable}"):
                st.write(a.description)
                st.markdown("**When to use it**")
                st.caption(a.when)
                st.markdown(f"**Method — {len(a.steps)} steps**")
                for i, s in enumerate(a.steps, 1):
                    st.markdown(f"{i:02d}. **{s.head}** {s.detail}")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**It needs from you**")
                    for x in a.inputs:
                        st.caption(f"· {x}")
                with c2:
                    st.markdown("**It hands back**")
                    for x in a.outputs:
                        st.caption(f"· {x}")
                st.caption(f"`skills/{a.slug}/SKILL.md`")
        st.write("")


# ── chat ─────────────────────────────────────────────────────────────────

def chat_panel(cfg: RunConfig) -> None:
    ss = st.session_state
    ui.eyebrow("Talk to the Deal Floor")

    all_keys = [m.key for m in providers.MODELS]
    usable = [
        k for k in all_keys
        if (providers.BY_KEY[k].vendor == "anthropic" and HAS_CLAUDE)
        or (providers.BY_KEY[k].vendor == "perplexity" and HAS_PPLX)
    ] or all_keys

    c1, c2 = st.columns([3, 1])
    with c1:
        model = st.selectbox(
            "Model", usable, format_func=lambda k: providers.BY_KEY[k].label,
            label_visibility="collapsed", key="chat_model",
        )
    with c2:
        if st.button("Clear", use_container_width=True):
            ss.chat = []
            st.rerun()

    attached = st.file_uploader(
        "Attach to this message",
        type=["pdf", "png", "jpg", "jpeg", "webp", "csv", "txt", "md", "docx", "xlsx"],
        accept_multiple_files=True,
        key="chat_files",
        label_visibility="collapsed",
    )

    box = st.container(height=430)
    with box:
        if not ss.chat:
            st.caption(
                "Ask what the agents found, challenge a number, or ask which "
                "agent to run next. The chat sees the deal file and every "
                "deliverable produced so far."
            )
        for turn in ss.chat:
            with st.chat_message(turn.role):
                st.markdown(turn.text)
                if turn.attachments:
                    st.caption("Attached: " + ", ".join(turn.attachments))
                if turn.citations:
                    ui.citations(turn.citations)
                if turn.model:
                    st.caption(turn.model)

    question = st.chat_input("Ask the desk…")
    if not question:
        return

    blocks, names = [], []
    for f in attached or []:
        src = intake.read(f.name, f.getvalue())
        names.append(f.name)
        if src.blocks:
            blocks.extend(src.blocks)
        elif src.text:
            blocks.append({
                "type": "text",
                "text": f"<attached name=\"{f.name}\">\n{src.text[:40000]}\n</attached>",
            })

    ss.chat.append(chat.Turn("user", question, attachments=names))
    with box, st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                reply = chat.ask(
                    question,
                    model_key=model,
                    history=ss.chat[:-1],
                    run=ss.run,
                    deal_file=ss.deal_file,
                    subject=cfg.subject,
                    attachments=blocks,
                    web_search=providers.BY_KEY[model].vendor == "anthropic",
                )
                ss.chat.append(chat.Turn(
                    "assistant", reply.text, reply.model, reply.citations
                ))
            except providers.ProviderError as exc:
                ss.chat.append(chat.Turn("assistant", f"⚠️ {exc}"))
    st.rerun()


# ── main ─────────────────────────────────────────────────────────────────

config = sidebar()
left, right = st.columns([1.45, 1], gap="large")

with left:
    tab_floor, tab_file, tab_out, tab_lib = st.tabs(
        ["Floor", "Deal file", "Output", "Library"]
    )
    with tab_floor:
        floor(config)
    with tab_file:
        deal_file_view()
    with tab_out:
        deliverables()
    with tab_lib:
        library()

with right:
    chat_panel(config)
