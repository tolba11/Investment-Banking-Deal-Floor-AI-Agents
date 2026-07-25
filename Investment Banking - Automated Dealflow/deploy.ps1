<#
    Create the GitHub repository and push this project to it. Windows version.

        .\deploy.ps1                    # private repo, default name
        .\deploy.ps1 -Public            # public repo
        .\deploy.ps1 -Name my-repo      # different name

    Uses the GitHub CLI's existing login on this machine. It never asks for a
    token and never stores a credential.
#>

param(
    [string]$Name = "investment-banking-deal-floor-ai-agents",
    [switch]$Public
)

$ErrorActionPreference = "Stop"
$Desc = "42 investment banking agents orchestrated over Claude and Perplexity"
$Visibility = if ($Public) { "--public" } else { "--private" }

function Say  { param($m) Write-Host "`n$m" -ForegroundColor White }
function Die  { param($m) Write-Host "`n$m" -ForegroundColor Red; exit 1 }

# ── preflight ────────────────────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Die "git is not installed.  winget install Git.Git"
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Die "GitHub CLI is not installed.  winget install GitHub.cli"
}

gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Die @"
GitHub CLI is not logged in. Run:  gh auth login
That opens your browser and authenticates on this machine. This script never
handles the token itself.
"@
}

$Account = (gh api user --jq .login).Trim()
Say "Signed in as $Account"

# ── never publish a key ──────────────────────────────────────────────────
if (Test-Path ".streamlit/secrets.toml") {
    git check-ignore -q ".streamlit/secrets.toml" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Say "secrets.toml found and correctly gitignored — it will not be pushed."
    } else {
        Die "secrets.toml exists but is NOT gitignored. Fix .gitignore before pushing."
    }
}

# ── repository ───────────────────────────────────────────────────────────
if (-not (Test-Path ".git")) { git init -q; Say "Initialised a git repository." }
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -q -m "Investment Banking - Deal Floor AI Agents"
}

gh repo view "$Account/$Name" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Say "Repository $Account/$Name already exists - pushing to it."
    git remote get-url origin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$Account/$Name.git"
    }
    git branch -M main
    git push -u origin main
} else {
    Say "Creating $Account/$Name"
    gh repo create $Name $Visibility --source=. --remote=origin --description $Desc --push
}

Say "Pushed to https://github.com/$Account/$Name"

Write-Host @"

Next - put it on Streamlit Community Cloud:

  1. https://share.streamlit.io  ->  Create app  ->  Deploy from GitHub
  2. Repository   $Account/$Name
     Branch       main
     Main file    app.py
  3. Advanced settings -> Secrets, paste:

       ANTHROPIC_API_KEY = "sk-ant-..."
       PERPLEXITY_API_KEY = "pplx-..."

  4. Deploy.

Paste the keys into Streamlit's own secrets box yourself - they belong in your
account, not in this repository.
"@
