#!/usr/bin/env bash
#
# Deploy argumentor to Google Cloud Run.
#
# Builds one image, runs `flask db upgrade` as a Cloud Run Job against it, then
# rolls out the web service using that same image. See DEPLOY.md for the
# one-time setup (project, Artifact Registry repo, secrets, service account).
#
# Usage:
#   ./scripts/deploy_cloudrun.sh
#
# Override any of these via the environment:
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-argumentor-449922}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-argumentor}"
JOB="${JOB:-argumentor-migrate}"
BACKUP_JOB="${BACKUP_JOB:-argumentor-backup}"
REPO="${REPO:-argumentor}"
RUNTIME_SA="${RUNTIME_SA:-argumentor-run@${PROJECT_ID}.iam.gserviceaccount.com}"
BACKUP_BUCKET="${BACKUP_BUCKET:-argumentor-449922-backups}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is not set and no gcloud default project is configured." >&2
  exit 1
fi

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:$(git rev-parse --short HEAD)"

# Every secret below must already exist in Secret Manager (see DEPLOY.md).
SECRETS="SECRET_KEY=SECRET_KEY:latest"
SECRETS+=",SQLALCHEMY_DATABASE_URI=SQLALCHEMY_DATABASE_URI:latest"
SECRETS+=",OPENAI_API_KEY=OPENAI_API_KEY:latest"
# GOOGLE_CLIENT_SECRET is deliberately absent: sign-in verifies an ID token
# against the client ID, which needs no secret. See config.py.
SECRETS+=",GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest"
SECRETS+=",MAIL_USERNAME=MAIL_USERNAME:latest"
SECRETS+=",MAIL_PASSWORD=MAIL_PASSWORD:latest"
SECRETS+=",MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER:latest"
SECRETS+=",STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest"
SECRETS+=",STRIPE_PUBLIC_KEY=STRIPE_PUBLIC_KEY:latest"
SECRETS+=",STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest"
SECRETS+=",STRIPE_PLUS_PRICE_ID=STRIPE_PLUS_PRICE_ID:latest"
SECRETS+=",STRIPE_PRO_PRICE_ID=STRIPE_PRO_PRICE_ID:latest"

# Non-secret config. GOOGLE_APPLICATION_CREDENTIALS is deliberately unset:
# src/extensions.py falls back to Application Default Credentials, which on
# Cloud Run resolves to the attached service account.
ENV_VARS="GCLOUD_PROJECT_NAME=${PROJECT_ID}"
ENV_VARS+=",GCLOUD_PROJECT_REGION=${GCLOUD_PROJECT_REGION:-us-central1}"
ENV_VARS+=",GCS_BUCKET=${GCS_BUCKET:-argumentor}"
# Per-worker pool caps. 2 workers x (2 + 3) x 3 max instances = 30 connections
# worst case, which stays under Supabase's pooler limit.
ENV_VARS+=",DB_POOL_SIZE=2,DB_MAX_OVERFLOW=3"

echo "==> Building ${IMAGE}"
gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID"

echo "==> Running migrations (Cloud Run Job)"
gcloud run jobs deploy "$JOB" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "$RUNTIME_SA" \
  --set-env-vars "FLASK_APP=src.app:app,${ENV_VARS}" \
  --set-secrets "$SECRETS" \
  --command flask \
  --args db,upgrade \
  --max-retries 1 \
  --task-timeout 10m

gcloud run jobs execute "$JOB" --region "$REGION" --project "$PROJECT_ID" --wait

echo "==> Deploying service"
# Free-tier guardrails:
#   --min-instances=0    scale to zero when idle (no charge while asleep)
#   default CPU throttling: CPU is billed only during request processing
#   --concurrency=12     matches gunicorn's 2 workers x 3 threads (+headroom);
#                        the Cloud Run default of 80 would oversubscribe them
#   --max-instances=3    caps the blast radius of a traffic spike
#
# Memory is 1Gi rather than the 512MB the Heroku dyno had. The app restarts its
# own workers at MEMORY_RESTART_THRESHOLD (250MB each, config.py), which on a
# 512Mi limit would race Cloud Run's own OOM kill. Heroku only logged R14 and
# kept the dyno alive; Cloud Run kills the whole instance. At 1Gi the app's
# graceful worker recycling stays the first line of defense.
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "$RUNTIME_SA" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 1Gi \
  --concurrency 12 \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 300 \
  --set-env-vars "$ENV_VARS" \
  --set-secrets "$SECRETS"

echo "==> Updating backup job"
# Supabase's free tier takes no backups, so this is the only copy of the data
# outside the live database. Scheduled separately (see DEPLOY.md).
gcloud run jobs deploy "$BACKUP_JOB" \
  --image "$IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "$RUNTIME_SA" \
  --set-env-vars "BACKUP_BUCKET=${BACKUP_BUCKET},BACKUP_RETENTION_DAYS=30" \
  --set-secrets "SQLALCHEMY_DATABASE_URI=SQLALCHEMY_DATABASE_URI:latest" \
  --command python \
  --args scripts/backup_db.py \
  --max-retries 2 \
  --task-timeout 30m

gcloud run services describe "$SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --format 'value(status.url)'
