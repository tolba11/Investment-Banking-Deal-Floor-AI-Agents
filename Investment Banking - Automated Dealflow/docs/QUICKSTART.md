# Quickstart

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Keys

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Add your Anthropic key. Perplexity is optional — without it, research agents
fall back to Claude with web search.

## 3. Run

```bash
streamlit run app.py
```

## 4. A first real run

1. **Attach documents.** Sidebar → the annual report, a CIQ pull, the model.
2. **Click "Read N documents".** Each is extracted into the deal file. The
   subject field fills itself from the first entity found.
3. **Open the Deal file tab and read it.** This is the fact base all 42 agents
   work from. Fix anything wrong here — it is one edit instead of 42.
4. **Pick "Valuation sprint"** (11 agents) for a first run rather than the
   full desk.
5. **Press Run mandate.** Stages complete in order; each agent's result lands
   in Output.
6. **Argue with it in the chat.** It sees every deliverable.
7. **Download the deal memo** from the Output tab.

## Troubleshooting

**"No API keys found"** — `.streamlit/secrets.toml` is missing or misnamed.
It must sit in `.streamlit/`, not the repo root.

**An agent failed with HTTP 429** — rate limited. Open it in Output and click
"Run this agent again". Nothing else is lost.

**A PDF came back empty** — it is probably scanned. Deal Floor sends those to
Claude as an image, so use a Claude model for intake, not Perplexity.

**The run seems frozen** — a stage of four agents on Opus takes 30–60s.
Progress appears per stage, not per agent.
