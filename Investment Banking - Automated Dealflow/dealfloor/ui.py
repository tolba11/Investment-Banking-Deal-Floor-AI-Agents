"""Theme and the few components worth sharing between views."""

from __future__ import annotations

import streamlit as st

from .catalog import Agent

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --line:#26303F; --line2:#323E51; --panel:#141B27; --panel2:#1A2230;
  --muted:#8494AB; --dim:#5A6982; --gold:#E8B44C; --jade:#55C79E; --rose:#D96B62;
}
html, body, [class*="css"]{ font-family:'IBM Plex Sans',system-ui,sans-serif; }
#MainMenu, footer, header{ visibility:hidden; }
.block-container{ padding-top:1.6rem; padding-bottom:2rem; max-width:100%; }

h1,h2,h3{ font-family:'IBM Plex Sans Condensed',sans-serif; letter-spacing:-.01em; }

.eyebrow{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--dim); }

.masthead{ display:flex; align-items:baseline; gap:12px; margin-bottom:2px; }
.masthead b{ font-family:'IBM Plex Sans Condensed',sans-serif; font-size:26px; font-weight:700; }
.masthead span{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:.14em; color:var(--dim); }

/* stage rail */
.stage{ border-left:2px solid var(--line); padding:2px 0 14px 15px; margin-left:5px; }
.stage.live{ border-left-color:var(--gold); }
.stage.done{ border-left-color:var(--jade); }
.stage h4{ font-family:'IBM Plex Sans Condensed',sans-serif; font-size:14px; font-weight:600;
  margin:0 0 8px; color:#E6EBF2; }
.stage h4 em{ font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:10px;
  color:var(--dim); margin-right:8px; }

.node{ position:relative; display:inline-flex; flex-direction:column; gap:2px;
  border:1px solid var(--line); border-radius:7px; background:var(--panel);
  padding:8px 12px 8px 13px; margin:0 7px 7px 0; min-width:172px; overflow:hidden; }
.node .kl{ position:absolute; left:0; top:0; bottom:0; width:2.5px; }
.node b{ font-family:'IBM Plex Sans Condensed',sans-serif; font-size:12.5px; font-weight:600; }
.node i{ font-style:normal; font-family:'IBM Plex Mono',monospace; font-size:9.5px; color:var(--dim); }
.node.done{ border-color:#2E5A4B; background:#131E1B; }
.node.done i{ color:var(--jade); }
.node.failed{ border-color:#6B3733; background:#1E1413; }
.node.failed i{ color:var(--rose); }
.node.live{ border-color:var(--gold); background:#1D1B12; }
.node.live i{ color:var(--gold); }

.pill{ display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:9.5px;
  letter-spacing:.06em; padding:3px 8px; border-radius:20px; border:1px solid var(--line2);
  color:var(--muted); margin:0 5px 5px 0; }
.pill.on{ border-color:#4A3A18; background:#1D1810; color:var(--gold); }

.factbase{ font-family:'IBM Plex Mono',monospace; font-size:11.5px; line-height:1.6; }
.cite{ font-family:'IBM Plex Mono',monospace; font-size:10.5px; color:var(--dim); }
.cite a{ color:var(--muted); }

.stChatMessage{ background:transparent; }
div[data-testid="stSidebarUserContent"]{ padding-top:1rem; }
</style>
"""

STATUS_MARK = {"idle": "·", "done": "✓", "failed": "✕", "live": "◆"}


def theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def masthead(title: str, kicker: str) -> None:
    st.markdown(
        f'<div class="masthead"><b>{title}</b><span>{kicker}</span></div>',
        unsafe_allow_html=True,
    )


def eyebrow(text: str) -> None:
    st.markdown(f'<div class="eyebrow">{text}</div>', unsafe_allow_html=True)


def node(agent: Agent, status: str, caption: str = "") -> str:
    cls = "" if status == "idle" else status
    label = caption or agent.deliverable
    return (
        f'<div class="node {cls}"><span class="kl" style="background:{agent.colour}"></span>'
        f'<b>{agent.title}</b><i>{STATUS_MARK.get(status, "·")} {label}</i></div>'
    )


def citations(urls: list[str], limit: int = 6) -> None:
    if not urls:
        return
    links = " · ".join(
        f'<a href="{u}" target="_blank">{_host(u)}</a>' for u in urls[:limit]
    )
    st.markdown(f'<div class="cite">Sources: {links}</div>', unsafe_allow_html=True)


def _host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc.replace("www.", "") or url[:38]
    except Exception:  # noqa: BLE001
        return url[:38]
