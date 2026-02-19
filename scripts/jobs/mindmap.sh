#!/usr/bin/env bash
set -euo pipefail

GITHUB_PAT=$(echo -n "$GITHUB_PAT" | tr -d '\n\r ')
REPO_URL="https://x-access-token:${GITHUB_PAT}@github.com/gail-yxie/awesome-asr.git"
WORKDIR="/workspace/awesome-asr"

echo "=== Weekly Mindmap Generator Job ==="
echo "Date: $(date -u +%Y-%m-%d) UTC"

# Configure git
git config --global user.name "cloud-run-jobs[bot]"
git config --global user.email "cloud-run-jobs[bot]@users.noreply.github.com"

# Clone repo (PAT embedded in URL for auth)
git clone --depth=1 "$REPO_URL" "$WORKDIR"
cd "$WORKDIR"

# Generate mindmap markdown
python -m scripts.mindmap.taxonomy_builder

# Render mindmaps to HTML
python -m scripts.mindmap.markmap_renderer

# Commit and push
git add mindmaps/ data/topic_taxonomy.json
git diff --cached --quiet || {
  git commit -m "mindmap: Regenerate ASR mindmaps"
  git pull --rebase origin main
  git push
}

echo "=== Mindmap generator complete ==="
