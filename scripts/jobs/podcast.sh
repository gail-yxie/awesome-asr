#!/usr/bin/env bash
set -euo pipefail

GITHUB_PAT=$(echo -n "$GITHUB_PAT" | tr -d '\n\r ')
REPO_URL="https://x-access-token:${GITHUB_PAT}@github.com/gail-yxie/awesome-asr.git"
REPO_SLUG="gail-yxie/awesome-asr"
WORKDIR="/workspace/awesome-asr"

echo "=== Weekly Podcast Generator Job ==="
echo "Date: $(date -u +%Y-%m-%d) UTC"

# Configure git + gh auth
git config --global user.name "cloud-run-jobs[bot]"
git config --global user.email "cloud-run-jobs[bot]@users.noreply.github.com"
echo "${GITHUB_PAT}" | gh auth login --with-token

# Clone repo (PAT embedded in URL for auth)
git clone --depth=1 "$REPO_URL" "$WORKDIR"
cd "$WORKDIR"

# Generate podcast script
python -m scripts.podcast.script_generator

# Generate podcast audio
python -m scripts.podcast.tts_engine

# Determine week tag
WEEK_TAG=$(date -u +%Y-W%V)

# Upload to GitHub Release
gh release create "podcast-${WEEK_TAG}" \
  --title "ASR Podcast — ${WEEK_TAG}" \
  --notes "Auto-generated weekly ASR podcast episode." \
  podcasts/*.mp3 || echo "Warning: release may already exist, continuing..."

# Update podcast index
MP3_URL="https://github.com/${REPO_SLUG}/releases/download/podcast-${WEEK_TAG}/${WEEK_TAG}.mp3"

if [ ! -f podcasts/index.md ]; then
  echo "# ASR Podcast Episodes" > podcasts/index.md
  echo "" >> podcasts/index.md
  echo "| Episode | Date | Audio |" >> podcasts/index.md
  echo "|---------|------|-------|" >> podcasts/index.md
fi

echo "| ${WEEK_TAG} | $(date -u +%Y-%m-%d) | [Listen](${MP3_URL}) |" >> podcasts/index.md

# Commit and push
git add podcasts/
git diff --cached --quiet || {
  git commit -m "podcast: Add episode for ${WEEK_TAG}"
  git pull --rebase origin main
  git push
}

echo "=== Podcast generator complete ==="
