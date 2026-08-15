#!/bin/bash
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
API_SERVICE="${AIOS_CLOUD_RUN_SERVICE:-aios-api}"
WEB_RUNTIME_SA_NAME="${AIOS_WEB_RUNTIME_SERVICE_ACCOUNT:-aios-web-runtime}"
WEB_RUNTIME_SA_EMAIL="${WEB_RUNTIME_SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
PASSWORD_SECRET="${AIOS_WEB_PASSWORD_SECRET:-aios-web-password}"

echo "=== AIOS WEB CAPTURE CLOUD SETUP ==="
echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Runtime: $WEB_RUNTIME_SA_EMAIL"

if ! gcloud iam service-accounts describe \
  "$WEB_RUNTIME_SA_EMAIL" \
  --project "$PROJECT" >/dev/null 2>&1
then
  gcloud iam service-accounts create \
    "$WEB_RUNTIME_SA_NAME" \
    --display-name="AIOS Web Capture runtime" \
    --project "$PROJECT"

  echo "Waiting briefly for IAM propagation..."
  sleep 8
fi

if ! gcloud secrets describe "$PASSWORD_SECRET" \
  --project "$PROJECT" >/dev/null 2>&1
then
  echo
  echo "Create the password used to open the Brain Dump web page."
  read -r -s -p "Password: " PASSWORD_ONE
  echo
  read -r -s -p "Confirm password: " PASSWORD_TWO
  echo

  if [ "$PASSWORD_ONE" != "$PASSWORD_TWO" ]; then
    echo "ERROR: passwords do not match."
    exit 1
  fi

  if [ "${#PASSWORD_ONE}" -lt 16 ]; then
    echo "ERROR: use a password of at least 16 characters."
    exit 1
  fi

  gcloud secrets create "$PASSWORD_SECRET" \
    --replication-policy=automatic \
    --project "$PROJECT"

  printf '%s' "$PASSWORD_ONE" | \
    gcloud secrets versions add "$PASSWORD_SECRET" \
      --data-file=- \
      --project "$PROJECT"

  unset PASSWORD_ONE PASSWORD_TWO
fi

gcloud secrets add-iam-policy-binding "$PASSWORD_SECRET" \
  --member="serviceAccount:${WEB_RUNTIME_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --project "$PROJECT" >/dev/null

gcloud run services add-iam-policy-binding "$API_SERVICE" \
  --member="serviceAccount:${WEB_RUNTIME_SA_EMAIL}" \
  --role="roles/run.invoker" \
  --project "$PROJECT" \
  --region "$REGION" >/dev/null

echo "Web Capture cloud setup complete."
