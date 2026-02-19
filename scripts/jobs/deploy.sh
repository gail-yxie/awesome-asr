#!/usr/bin/env bash
#
# Deploy awesome-asr Cloud Run Jobs + Cloud Scheduler
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated (gcloud auth login)
#   2. A GCP project created
#   3. A GitHub fine-grained PAT with contents:write on gail-yxie/awesome-asr
#
# Usage:
#   GCP_PROJECT_ID=my-project ./scripts/jobs/deploy.sh
#
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID env var}"
REGION="${GCP_REGION:-us-central1}"
REPO_NAME="awesome-asr"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/jobs:latest"
SA_NAME="awesome-asr-jobs"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Deploying awesome-asr jobs to GCP ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo ""

# -------------------------------------------------------
# 1. Enable required APIs
# -------------------------------------------------------
echo "--- Enabling APIs ---"
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

# -------------------------------------------------------
# 2. Create Artifact Registry repository
# -------------------------------------------------------
echo "--- Setting up Artifact Registry ---"
gcloud artifacts repositories describe "$REPO_NAME" \
  --location="$REGION" --project="$PROJECT_ID" 2>/dev/null \
  || gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID"

# -------------------------------------------------------
# 3. Create service account
# -------------------------------------------------------
echo "--- Setting up service account ---"
gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" 2>/dev/null \
  || gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Awesome ASR Jobs" \
    --project="$PROJECT_ID"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  --quiet

# Grant Cloud Run Invoker (so Cloud Scheduler can trigger jobs)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker" \
  --condition=None \
  --quiet

# -------------------------------------------------------
# 4. Create secrets (prints instructions for missing ones)
# -------------------------------------------------------
echo "--- Checking secrets ---"
SECRETS=(GITHUB_PAT GEMINI_API_KEY HF_TOKEN TWITTER_BEARER_TOKEN \
         SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_FROM_ADDRESS)
MISSING=()

for SECRET in "${SECRETS[@]}"; do
  if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" &>/dev/null; then
    MISSING+=("$SECRET")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo ""
  echo "The following secrets need to be created:"
  for SECRET in "${MISSING[@]}"; do
    echo "  echo -n 'VALUE' | gcloud secrets create ${SECRET} --data-file=- --project=${PROJECT_ID}"
  done
  echo ""
  echo "Create the required secrets (at minimum GITHUB_PAT and GEMINI_API_KEY) then re-run this script."
  exit 1
fi

# -------------------------------------------------------
# 5. Build and push Docker image via Cloud Build
# -------------------------------------------------------
echo "--- Building and pushing Docker image (via Cloud Build) ---"
gcloud services enable cloudbuild.googleapis.com --project="${PROJECT_ID}"
gcloud builds submit \
  --tag="$IMAGE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --gcs-log-dir="gs://${PROJECT_ID}_cloudbuild/logs" \
  --dockerfile=Dockerfile.jobs \
  .

# -------------------------------------------------------
# 6. Create / update Cloud Run Jobs
# -------------------------------------------------------
echo "--- Creating Cloud Run Jobs ---"

create_or_update_job() {
  local JOB_NAME="$1"
  shift
  if gcloud run jobs describe "$JOB_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Updating job: $JOB_NAME"
    gcloud run jobs update "$JOB_NAME" "$@" --region="$REGION" --project="$PROJECT_ID"
  else
    echo "Creating job: $JOB_NAME"
    gcloud run jobs create "$JOB_NAME" "$@" --region="$REGION" --project="$PROJECT_ID"
  fi
}

# Daily Tracker
create_or_update_job awesome-asr-daily \
  --image="$IMAGE" \
  --command="/bin/bash" \
  --args="/app/jobs/daily.sh" \
  --set-secrets="GITHUB_PAT=GITHUB_PAT:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,HF_TOKEN=HF_TOKEN:latest,TWITTER_BEARER_TOKEN=TWITTER_BEARER_TOKEN:latest,SMTP_HOST=SMTP_HOST:latest,SMTP_PORT=SMTP_PORT:latest,SMTP_USER=SMTP_USER:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest,SMTP_FROM_ADDRESS=SMTP_FROM_ADDRESS:latest" \
  --set-env-vars="SITE_URL=https://asr.example.com,TTS_BACKEND=gemini" \
  --service-account="$SA_EMAIL" \
  --memory=2Gi \
  --cpu=1 \
  --task-timeout=30m \
  --max-retries=1

# Podcast Generator
create_or_update_job awesome-asr-podcast \
  --image="$IMAGE" \
  --command="/bin/bash" \
  --args="/app/jobs/podcast.sh" \
  --set-secrets="GITHUB_PAT=GITHUB_PAT:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,HF_TOKEN=HF_TOKEN:latest" \
  --set-env-vars="TTS_BACKEND=gemini" \
  --service-account="$SA_EMAIL" \
  --memory=4Gi \
  --cpu=2 \
  --task-timeout=60m \
  --max-retries=1

# Mindmap Generator
create_or_update_job awesome-asr-mindmap \
  --image="$IMAGE" \
  --command="/bin/bash" \
  --args="/app/jobs/mindmap.sh" \
  --set-secrets="GITHUB_PAT=GITHUB_PAT:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --service-account="$SA_EMAIL" \
  --memory=2Gi \
  --cpu=1 \
  --task-timeout=30m \
  --max-retries=1

# -------------------------------------------------------
# 7. Create / update Cloud Scheduler triggers
# -------------------------------------------------------
echo "--- Creating Cloud Scheduler triggers ---"

create_or_update_schedule() {
  local SCHED_NAME="$1"
  local CRON="$2"
  local JOB_NAME="$3"
  local URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

  if gcloud scheduler jobs describe "$SCHED_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Updating schedule: $SCHED_NAME"
    gcloud scheduler jobs update http "$SCHED_NAME" \
      --location="$REGION" \
      --schedule="$CRON" \
      --time-zone="UTC" \
      --uri="$URI" \
      --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      --project="$PROJECT_ID"
  else
    echo "Creating schedule: $SCHED_NAME"
    gcloud scheduler jobs create http "$SCHED_NAME" \
      --location="$REGION" \
      --schedule="$CRON" \
      --time-zone="UTC" \
      --uri="$URI" \
      --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      --project="$PROJECT_ID"
  fi
}

# Daily at 06:00 UTC
create_or_update_schedule awesome-asr-daily-schedule "0 6 * * *" awesome-asr-daily

# Podcast: Sundays at 12:00 UTC
create_or_update_schedule awesome-asr-podcast-schedule "0 12 * * 0" awesome-asr-podcast

# Mindmap: Sundays at 14:00 UTC
create_or_update_schedule awesome-asr-mindmap-schedule "0 14 * * 0" awesome-asr-mindmap

# -------------------------------------------------------
# Done
# -------------------------------------------------------
echo ""
echo "=== Deployment complete ==="
echo ""
echo "Test manually:"
echo "  gcloud run jobs execute awesome-asr-daily   --region=${REGION} --project=${PROJECT_ID}"
echo "  gcloud run jobs execute awesome-asr-podcast  --region=${REGION} --project=${PROJECT_ID}"
echo "  gcloud run jobs execute awesome-asr-mindmap  --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "View logs:"
echo "  gcloud logging read 'resource.type=\"cloud_run_job\"' --project=${PROJECT_ID} --limit=50"
