"""Unified access to Claude and Perplexity.

Every call returns a Reply, whichever vendor served it, so the rest of the
codebase never branches on provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable

ANTHROPIC_BASE = "https://api.anthropic.com"
PERPLEXITY_BASE = "https://api.perplexity.ai"


@dataclass(frozen=True)
class Model:
    key: str
    label: str
    vendor: str          # "anthropic" | "perplexity"
    api_name: str
    note: str
    searches: bool = False   # reaches the live web without being asked


MODELS: tuple[Model, ...] = (
    Model("opus-4.8", "Claude Opus 4.8", "anthropic", "claude-opus-4-8",
          "Deepest reasoning. The default for valuation and structuring."),
    Model("fable-5", "Claude Fable 5", "anthropic", "claude-fable-5",
          "Mythos tier, with added safeguards. Strongest long-form judgement."),
    Model("sonnet-5", "Claude Sonnet 5", "anthropic", "claude-sonnet-5",
          "Fast and capable. Good default for a full 42-agent run."),
    Model("haiku-4.5", "Claude Haiku 4.5", "anthropic", "claude-haiku-4-5-20251001",
          "Cheapest and quickest. Fine for intake and PMO agents."),
    Model("sonar-pro", "Perplexity Sonar Pro", "perplexity", "sonar-pro",
          "Live web with rich citations. Best for comps and precedents.", True),
    Model("sonar", "Perplexity Sonar", "perplexity", "sonar",
          "Live web, cheap. Good for quick market colour.", True),
    Model("sonar-reasoning-pro", "Perplexity Sonar Reasoning Pro", "perplexity",
          "sonar-reasoning-pro", "Search plus chain-of-thought. Slower.", True),
    Model("sonar-deep-research", "Perplexity Deep Research", "perplexity",
          "sonar-deep-research",
          "Runs many searches per call. Expensive and slow — use sparingly.", True),
)

BY_KEY = {m.key: m for m in MODELS}
ANTHROPIC_MODELS = [m for m in MODELS if m.vendor == "anthropic"]
PERPLEXITY_MODELS = [m for m in MODELS if m.vendor == "perplexity"]


@dataclass
class Reply:
    text: str
    model: str
    vendor: str
    citations: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ProviderError(RuntimeError):
    """A call failed in a way the caller should surface, not swallow."""


def _key(vendor: str) -> str:
    env = "ANTHROPIC_API_KEY" if vendor == "anthropic" else "PERPLEXITY_API_KEY"
    val = os.environ.get(env, "").strip()
    if not val:
        raise ProviderError(
            f"{env} is not set. Add it to .streamlit/secrets.toml or your environment."
        )
    return val


def available(vendor: str) -> bool:
    env = "ANTHROPIC_API_KEY" if vendor == "anthropic" else "PERPLEXITY_API_KEY"
    return bool(os.environ.get(env, "").strip())


# ── Anthropic ────────────────────────────────────────────────────────────

def _anthropic(
    model: Model,
    system: str,
    content: list[dict[str, Any]],
    max_tokens: int,
    web_search: bool,
    history: Iterable[dict[str, Any]] = (),
) -> Reply:
    import anthropic

    client = anthropic.Anthropic(api_key=_key("anthropic"), base_url=ANTHROPIC_BASE)
    kwargs: dict[str, Any] = {
        "model": model.api_name,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [*history, {"role": "user", "content": content}],
    }
    if web_search:
        kwargs["tools"] = [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 6}
        ]

    try:
        msg = client.messages.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 — surfaced verbatim to the operator
        raise ProviderError(f"Claude call failed: {exc}") from exc

    parts, cites = [], []
    for block in msg.content:
        btype = getattr(block, "type", "")
        if btype == "text":
            parts.append(block.text)
            for cite in getattr(block, "citations", None) or []:
                url = getattr(cite, "url", None)
                if url:
                    cites.append(url)
        elif btype == "web_search_tool_result":
            for item in getattr(block, "content", None) or []:
                url = getattr(item, "url", None)
                if url:
                    cites.append(url)

    text = "\n".join(p for p in parts if p).strip()
    if not text:
        raise ProviderError("Claude returned an empty response.")

    usage = getattr(msg, "usage", None)
    return Reply(
        text=text,
        model=model.label,
        vendor="anthropic",
        citations=_dedupe(cites),
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
    )


# ── Perplexity ───────────────────────────────────────────────────────────

def _perplexity(
    model: Model,
    system: str,
    content: list[dict[str, Any]],
    max_tokens: int,
    history: Iterable[dict[str, Any]] = (),
) -> Reply:
    """Perplexity speaks the OpenAI chat shape.

    It takes text and images but not PDFs, so PDF pages arrive here already
    flattened to text by intake.extract().
    """
    from openai import OpenAI

    client = OpenAI(api_key=_key("perplexity"), base_url=PERPLEXITY_BASE)

    converted: list[dict[str, Any]] = []
    for block in content:
        if block.get("type") == "text":
            converted.append({"type": "text", "text": block["text"]})
        elif block.get("type") == "image":
            src = block["source"]
            converted.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{src['media_type']};base64,{src['data']}"
                },
            })
        elif block.get("type") == "document":
            converted.append({
                "type": "text",
                "text": "[A PDF was attached. Its text is included above.]",
            })

    try:
        resp = client.chat.completions.create(
            model=model.api_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                *history,
                {"role": "user", "content": converted},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"Perplexity call failed: {exc}") from exc

    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise ProviderError("Perplexity returned an empty response.")

    cites = list(getattr(resp, "citations", None) or [])
    if not cites:
        for item in getattr(resp, "search_results", None) or []:
            url = item.get("url") if isinstance(item, dict) else None
            if url:
                cites.append(url)

    usage = getattr(resp, "usage", None)
    return Reply(
        text=text,
        model=model.label,
        vendor="perplexity",
        citations=_dedupe(cites),
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
    )


# ── public ───────────────────────────────────────────────────────────────

def complete(
    model_key: str,
    system: str,
    content: str | list[dict[str, Any]],
    *,
    max_tokens: int = 1400,
    web_search: bool = False,
    history: Iterable[dict[str, Any]] = (),
) -> Reply:
    """Call whichever vendor owns `model_key` and normalise the result."""
    model = BY_KEY.get(model_key)
    if model is None:
        raise ProviderError(f"Unknown model '{model_key}'.")

    blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content

    if model.vendor == "anthropic":
        return _anthropic(model, system, blocks, max_tokens, web_search, history)
    return _perplexity(model, system, blocks, max_tokens, history)


def _dedupe(urls: list[str]) -> list[str]:
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out
