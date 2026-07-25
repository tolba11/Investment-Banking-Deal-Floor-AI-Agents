# Investment Banking — Deal Floor AI Agents

**42 investment banking agents, orchestrated over Claude and Perplexity.**

Each agent is a `SKILL.md` file with a named method — eight numbered steps, a
declared input list, a fixed output format. Deal Floor chains them into
mandates, runs them against documents you attach, and gives you one place to
argue with the result.

Not a chatbot with a banking system prompt. Forty-two methods that run in
order and hand work to each other.

---

## What it does

**Attach the documents first.** Annual report, CIQ pull, the model, a
PitchBook screenshot. Each source is read once into a *deal file* — a
structured fact base of income statement, capital structure, cash flow,
segment KPIs, guidance, one-offs. Every agent then works from that fact base,
so 42 calls don't each re-read a 200-page PDF.

The deal file is editable. It is the single point where an extraction error
would propagate to all 42 agents, and the single place you can fix it.

**Run a mandate.** Six chains ship with the project:

| Mandate | Agents | What it produces |
|---|---|---|
| Sell-side M&A | 27 | Market read → model → three valuation methods → CIM → buyer list → diligence → close |
| Buy-side acquisition | 22 | Target baseline → accretion/dilution → diligence → structure → offer |
| Sponsor LBO | 18 | Buyout model → debt sizing → syndication → returns stress |
| Capital raise | 22 | Financing plan → investor map → roadshow → term sheet |
| Valuation sprint | 11 | One defensible range, cross-checked three ways |
| Full desk | 42 | Every agent, front to back |

Stages run in order. Agents within a stage run in parallel. Each agent sees
the deal file plus the deliverables from earlier stages, so the chain
accumulates.

**Talk to the desk.** The chat panel sees the deal file, the agent roster, and
every deliverable produced so far. Ask *"what did DCF Modeling assume for
WACC?"* and it answers from the actual output, not from scratch. Attach a
document mid-conversation and it reads it.

---

## Model routing

Nine agents whose method is fundamentally *"find out what is true right now"*
route to a live-search model. The other 33 reason over the deal file and never
touch the web.

| | Agents | Default |
|---|---|---|
| **Research** | Market Intelligence, Industry Analysis, Company Research, Comparable Analysis, Precedent Transactions, Buyer Targeting, Investor Targeting, Debt Sourcing, Equity Sourcing | Perplexity Sonar Pro |
| **Analysis** | The other 33 | Claude Opus 5 & 4.8 |
| **Intake** | Reads each source document | Claude Haiku 4.5 |

All three are switchable in the sidebar. Available models: Claude Opus 5 & 4.8,
Fable 5, Sonnet 5, Haiku 4.5; Perplexity Sonar, Sonar Pro, Sonar Reasoning
Pro, Deep Research.

Perplexity is optional. Without a key, research agents fall back to Claude
with web search enabled.

---

## Run it

```bash
git clone https://github.com/YOUR-USERNAME/investment-banking-deal-floor-ai-agents.git
cd investment-banking-deal-floor-ai-agents
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# add your keys

streamlit run app.py
```

Opens at `http://localhost:8501`.

### Keys

```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-..."
PERPLEXITY_API_KEY = "pplx-..."   # optional
```

Environment variables of the same names also work. `secrets.toml` is
gitignored.

### Deploy

```bash
./deploy.sh --public      # macOS / Linux / Git Bash
.\deploy.ps1 -Public      # Windows PowerShell
```

Creates the repository and pushes. Then point Streamlit Community Cloud at
`app.py`. Full walkthrough in [DEPLOY.md](DEPLOY.md).

---

## Cost

A full 42-agent run is 42 calls plus one per document. On Opus 4.8 with
Sonar Pro for research that lands around **$2–5** depending on how much
deal file each agent carries.

Cheaper: put Sonnet 5 or Haiku 4.5 on analysis. Avoid Perplexity Deep
Research unless you mean it — it runs many searches per call.

Start with **Valuation sprint** (11 agents) before committing to a full desk run.

---

## Layout

```
app.py                  Streamlit UI — sidebar, floor, chat
deploy.sh / deploy.ps1  Create the repo and push
dealfloor/
  catalog.py            The 42 agents, mandates, prompt construction
  providers.py          Claude + Perplexity behind one Reply type
  intake.py             Documents → deal file
  orchestrator.py       Stage-by-stage execution
  chat.py               Deal-aware conversation
  ui.py                 Theme and shared components
  build.py              Regenerate the catalogue from skills/
skills/<slug>/SKILL.md  The 42 agents. Source of truth.
data/agents.json        Parsed catalogue. Generated.
tests/                  pytest
```

### Editing an agent

Edit `skills/<slug>/SKILL.md`, then:

```bash
python -m dealfloor.build
```

The method steps become the agent's system prompt verbatim, so changing the
skill changes the behaviour with no code edit.

### Adding a mandate

Add an entry to `mandates` in `data/agents.json`:

```json
{
  "id": "carve-out",
  "name": "Carve-out",
  "sub": "Separate a division and sell it",
  "stages": [
    ["Baseline the unit", ["company-research", "industry-analysis"]],
    ["Standalone economics", ["financial-modeling", "capital-structure"]]
  ]
}
```

---

## Tests

```bash
pip install pytest
pytest -q
```

Providers are stubbed; the suite makes no network calls and needs no keys.

---

## Known limits

- **Outputs are ~500 words per agent.** Tight, numerate desk output — a real
  football field, a real WACC build. Not a 19-sheet Excel workbook.
- **Intake caps at ~450 words per document.** A dense annual report may need
  splitting across two attachments to capture everything.
- **A long run blocks the tab.** Streamlit is single-threaded per session;
  stages run in parallel internally but the page waits. Results are saved per
  agent as they land, so an interrupted run keeps what it finished.
- **Agents can be wrong.** They mark estimates as estimates and the deal file
  overrides them, but nothing here removes the need to check the numbers.

---

## Licence

MIT. See [LICENSE](LICENSE).

The 42 skill definitions are included so the project runs out of the box.
Adapt them — they are the interesting part.
