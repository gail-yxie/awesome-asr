#!/usr/bin/env bash
set -euo pipefail

GITHUB_PAT=$(echo -n "$GITHUB_PAT" | tr -d '\n\r ')
REPO_URL="https://x-access-token:${GITHUB_PAT}@github.com/gail-yxie/awesome-asr.git"
WORKDIR="/workspace/awesome-asr"

echo "=== Daily ASR Tracker Job ==="
echo "Date: $(date -u +%Y-%m-%d) UTC"

# Configure git
git config --global user.name "cloud-run-jobs[bot]"
git config --global user.email "cloud-run-jobs[bot]@users.noreply.github.com"

# Clone repo (PAT embedded in URL for auth)
git clone --depth=1 "$REPO_URL" "$WORKDIR"
cd "$WORKDIR"

# Run daily tracker
python -m scripts.tracking.aggregator

# Update README
python -m scripts.readme.readme_updater

# Send daily email (only if SMTP is configured)
if [ -n "${SMTP_HOST:-}" ]; then
  python -m scripts.email.sender || echo "Warning: email sending failed, continuing..."
fi

# Commit and push
git add daily/ README.md data/
git diff --cached --quiet || {
  git commit -m "daily: Add ASR update for $(date -u +%Y-%m-%d)"
  git pull --rebase origin main
  git push
}

echo "=== Daily tracker complete ==="
