#!/usr/bin/env bash
#
# Create the GitHub repository and push this project to it.
#
#   ./deploy.sh                    # private repo, default name
#   ./deploy.sh --public           # public repo
#   ./deploy.sh --name my-repo     # different name
#
# This uses the GitHub CLI's existing login on this machine. It never asks for
# a token and never stores a credential.

set -euo pipefail

NAME="investment-banking-deal-floor-ai-agents"
DESC="42 investment banking agents orchestrated over Claude and Perplexity"
VISIBILITY="--private"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --public)  VISIBILITY="--public"; shift ;;
    --private) VISIBILITY="--private"; shift ;;
    --name)    NAME="$2"; shift 2 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
die() { printf '\n\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

# ── preflight ────────────────────────────────────────────────────────────
command -v git >/dev/null || die "git is not installed."
command -v gh  >/dev/null || die "GitHub CLI is not installed.
  macOS    brew install gh
  Windows  winget install GitHub.cli
  Linux    see https://github.com/cli/cli#installation"

if ! gh auth status >/dev/null 2>&1; then
  die "GitHub CLI is not logged in. Run:  gh auth login
That opens your browser and authenticates on this machine. This script never
handles the token itself."
fi

ACCOUNT=$(gh api user --jq .login)
say "Signed in as $ACCOUNT"

# ── never publish a key ──────────────────────────────────────────────────
if [[ -f .streamlit/secrets.toml ]] && git check-ignore -q .streamlit/secrets.toml; then
  say "secrets.toml found and correctly gitignored — it will not be pushed."
elif [[ -f .streamlit/secrets.toml ]]; then
  die "secrets.toml exists but is NOT gitignored. Fix .gitignore before pushing."
fi

# ── repository ───────────────────────────────────────────────────────────
[[ -d .git ]] || { git init -q; say "Initialised a git repository."; }
git add -A
git diff --cached --quiet || git commit -q -m "Investment Banking — Deal Floor AI Agents"

if gh repo view "$ACCOUNT/$NAME" >/dev/null 2>&1; then
  say "Repository $ACCOUNT/$NAME already exists — pushing to it."
  git remote get-url origin >/dev/null 2>&1 \
    || git remote add origin "https://github.com/$ACCOUNT/$NAME.git"
  git branch -M main
  git push -u origin main
else
  say "Creating $ACCOUNT/$NAME"
  gh repo create "$NAME" $VISIBILITY --source=. --remote=origin \
     --description "$DESC" --push
fi

URL="https://github.com/$ACCOUNT/$NAME"
say "Pushed to $URL"

cat <<EOF

Next — put it on Streamlit Community Cloud:

  1. https://share.streamlit.io  →  Create app  →  Deploy from GitHub
  2. Repository   $ACCOUNT/$NAME
     Branch       main
     Main file    app.py
  3. Advanced settings → Secrets, paste:

       ANTHROPIC_API_KEY = "sk-ant-..."
       PERPLEXITY_API_KEY = "pplx-..."

  4. Deploy.

Paste the keys into Streamlit's own secrets box yourself — they belong in your
account, not in this repository.
EOF
