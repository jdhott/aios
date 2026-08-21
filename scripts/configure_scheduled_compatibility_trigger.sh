#!/bin/bash
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
SERVICE="${AIOS_CLOUD_RUN_SERVICE:-aios-api}"
TIME_ZONE="${AIOS_SCHEDULER_TIME_ZONE:-America/Toronto}"
SCHEDULER_SA_NAME="${AIOS_SCHEDULER_SERVICE_ACCOUNT:-aios-scheduler}"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

QUARTER_HOUR_JOB="aios-compat-quarter-hour"
FINAL_JOB="aios-compat-2100"

echo "=== AIOS SCHEDULED COMPATIBILITY TRIGGER ==="
echo "Project:    $PROJECT"
echo "Region:     $REGION"
echo "Service:    $SERVICE"
echo "Timezone:   $TIME_ZONE"
echo "Caller:     $SCHEDULER_SA_EMAIL"
echo "Schedules:"
echo "  */30 5-20 * * *"
echo "  0 21 * * *"

gcloud services enable \
  cloudscheduler.googleapis.com \
  --project "$PROJECT"

if ! gcloud iam service-accounts describe \
  "$SCHEDULER_SA_EMAIL" \
  --project "$PROJECT" >/dev/null 2>&1
then
  gcloud iam service-accounts create \
    "$SCHEDULER_SA_NAME" \
    --display-name="AIOS Cloud Scheduler caller" \
    --project "$PROJECT"
fi

gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="serviceAccount:${SCHEDULER_SA_EMAIL}" \
  --role="roles/run.invoker" >/dev/null

SERVICE_URL="$(
  gcloud run services describe "$SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --format='value(status.url)'
)"

if [ -z "$SERVICE_URL" ]; then
  echo "ERROR: Could not resolve Cloud Run service URL."
  exit 1
fi

TARGET_URL="${SERVICE_URL}/processing/request"

create_or_update() {
  local name="$1"
  local schedule="$2"

  if gcloud scheduler jobs describe "$name" \
      --project "$PROJECT" \
      --location "$REGION" >/dev/null 2>&1
  then
    echo "Updating Scheduler job: $name"
    gcloud scheduler jobs update http "$name" \
      --project "$PROJECT" \
      --location "$REGION" \
      --schedule "$schedule" \
      --time-zone "$TIME_ZONE" \
      --uri "$TARGET_URL" \
      --http-method POST \
      --oidc-service-account-email "$SCHEDULER_SA_EMAIL" \
      --oidc-token-audience "$SERVICE_URL" \
      --attempt-deadline 60s \
      --max-retry-attempts 3 \
      --min-backoff 10s \
      --max-backoff 60s \
      --max-doublings 2
  else
    echo "Creating Scheduler job: $name"
    gcloud scheduler jobs create http "$name" \
      --project "$PROJECT" \
      --location "$REGION" \
      --schedule "$schedule" \
      --time-zone "$TIME_ZONE" \
      --uri "$TARGET_URL" \
      --http-method POST \
      --oidc-service-account-email "$SCHEDULER_SA_EMAIL" \
      --oidc-token-audience "$SERVICE_URL" \
      --attempt-deadline 60s \
      --max-retry-attempts 3 \
      --min-backoff 10s \
      --max-backoff 60s \
      --max-doublings 2
  fi
}

create_or_update "$QUARTER_HOUR_JOB" "*/30 5-20 * * *"
create_or_update "$FINAL_JOB" "0 21 * * *"

echo
echo "Configured schedules successfully."
echo "The Scheduler invokes the private API; it does NOT call the processor Job directly."
echo
echo "Verify with:"
echo "  gcloud scheduler jobs list --project $PROJECT --location $REGION"
