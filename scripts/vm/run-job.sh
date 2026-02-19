#!/usr/bin/env bash
# Unified cron job wrapper for awesome-asr.
# Usage: run-job.sh {daily|podcast|mindmap}
set -euo pipefail

JOB_TYPE="${1:-}"
REPO_DIR="/opt/awesome-asr/repo"
VENV="/opt/awesome-asr/venv"
LOG_DIR="/opt/awesome-asr/logs"
ENV_FILE="/opt/awesome-asr/.env"

if [[ -z "$JOB_TYPE" ]]; then
  echo "Usage: $0 {daily|podcast|mindmap}"
  exit 1
fi

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
LOG_FILE="${LOG_DIR}/${JOB_TYPE}-${TIMESTAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== ${JOB_TYPE} job started at $(date -u) ==="

# Load environment and activate venv
set -a
source "$ENV_FILE"
set +a
source "${VENV}/bin/activate"

# Configure git
git config --global user.name "vm-jobs[bot]"
git config --global user.email "vm-jobs[bot]@users.noreply.github.com"

cd "$REPO_DIR"

# Pull latest changes
git pull --rebase origin main

GITHUB_PAT=$(echo -n "$GITHUB_PAT" | tr -d '\n\r ')
REPO_SLUG="${GITHUB_REPO_SLUG:-$(git remote get-url origin | sed 's|.*github.com[:/]||;s|\.git$||')}"

case "$JOB_TYPE" in
  daily)
    python -m scripts.tracking.aggregator
    python -m scripts.readme.readme_updater
    if [[ -n "${SMTP_HOST:-}" ]]; then
      python -m scripts.email.sender || echo "Warning: email sending failed"
    fi
    git add daily/ README.md data/
    ;;

  podcast)
    python -m scripts.podcast.script_generator
    python -m scripts.podcast.tts_engine
    DAY_TAG=$(date -u +%Y-%m-%d)
    # Upload to GitHub Release if gh is configured
    if command -v gh &>/dev/null && [[ -n "$GITHUB_PAT" ]]; then
      echo "$GITHUB_PAT" | gh auth login --with-token 2>/dev/null
      gh release create "podcast-${DAY_TAG}" \
        --repo "$REPO_SLUG" \
        --title "ASR Podcast — ${DAY_TAG}" \
        --notes "Auto-generated ASR podcast episode." \
        podcasts/*.mp3 2>/dev/null \
        || echo "Warning: release may already exist"
    fi
    git add podcasts/
    ;;

  mindmap)
    python -m scripts.mindmap.taxonomy_builder
    python -m scripts.mindmap.markmap_renderer
    git add mindmaps/ data/topic_taxonomy.json
    ;;

  *)
    echo "Unknown job type: $JOB_TYPE"
    exit 1
    ;;
esac

# Commit and push if there are changes
git diff --cached --quiet || {
  git commit -m "${JOB_TYPE}: Auto-update for $(date -u +%Y-%m-%d)"
  PUSH_URL="https://x-access-token:${GITHUB_PAT}@github.com/${REPO_SLUG}.git"
  git push "$PUSH_URL" main
}

echo "=== ${JOB_TYPE} job completed at $(date -u) ==="

# Clean up logs older than 30 days
find "$LOG_DIR" -name "${JOB_TYPE}-*.log" -mtime +30 -delete 2>/dev/null || true
