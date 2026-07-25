# Deploying

Two steps: push to GitHub, then point Streamlit at it.

Both need credentials that live on **your** machine and in **your** browser.
Nothing here asks you to paste a token into a file or share one with anyone.

---

## 1. GitHub

### One command

```bash
# macOS / Linux / Git Bash / WSL
./deploy.sh --public

# Windows PowerShell
.\deploy.ps1 -Public
```

Drop the `--public` / `-Public` flag for a private repository.

The script checks `git` and `gh` are installed, confirms you're logged in,
verifies `secrets.toml` is gitignored before anything leaves the machine,
creates `investment-banking-deal-floor-ai-agents`, and pushes.

### First time only

```bash
gh auth login
```

Opens your browser, authenticates the CLI against your account, stores the
credential in your system keychain. The scripts here read that existing login —
they never see or store the token.

Don't have the CLI:

| | |
|---|---|
| Windows | `winget install GitHub.cli` |
| macOS | `brew install gh` |
| Linux | [cli.github.com](https://cli.github.com) |

### By hand

```bash
git init
git add -A
git commit -m "Investment Banking - Deal Floor AI Agents"
gh repo create investment-banking-deal-floor-ai-agents --public --source=. --push
```

Or create the repo in the GitHub web UI and:

```bash
git remote add origin https://github.com/YOUR-USERNAME/investment-banking-deal-floor-ai-agents.git
git branch -M main
git push -u origin main
```

---

## 2. Streamlit Community Cloud

1. [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
2. **Create app** → **Deploy from GitHub**
3. Fill in:

   | Field | Value |
   |---|---|
   | Repository | `YOUR-USERNAME/investment-banking-deal-floor-ai-agents` |
   | Branch | `main` |
   | Main file path | `app.py` |

4. **Advanced settings → Secrets**, paste:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   PERPLEXITY_API_KEY = "pplx-..."
   ```

5. **Deploy.** First build takes 2–3 minutes.

Streamlit's secrets box writes to your app's own encrypted store. It is the
right place for these keys — not the repository, not a committed file.

### After deploying

Pushing to `main` redeploys automatically. To edit an agent:

```bash
vim skills/dcf-modeling/SKILL.md
python -m dealfloor.build     # refresh the catalogue
pytest -q
git commit -am "Sharpen the DCF terminal value cross-check"
git push
```

---

## Private repositories

Streamlit Community Cloud deploys from private repos on the free tier, but you
must grant it access when you first sign in — accept the GitHub authorisation
prompt asking for repository permissions.

---

## If it fails

**`gh: command not found`** — CLI not installed. See the table above.

**`gh auth status` fails** — run `gh auth login`.

**`repository already exists`** — the script detects this and pushes to it
instead. To use a different name: `./deploy.sh --name something-else`.

**Streamlit build fails on `ModuleNotFoundError`** — `requirements.txt` didn't
get committed. Check `git ls-files | grep requirements`.

**App loads but says "No API keys found"** — the secrets weren't saved. Open
the app's **⋮ → Settings → Secrets** and paste them there.

**`secrets.toml exists but is NOT gitignored`** — the script stopped you from
publishing a key. Confirm `.gitignore` contains `.streamlit/secrets.toml`.
