#!/bin/bash
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
JOB="${AIOS_CLOUD_RUN_JOB:-aios-processor}"
API_SERVICE_ACCOUNT="${AIOS_API_RUNTIME_SERVICE_ACCOUNT_EMAIL:-aios-api-runtime@${PROJECT}.iam.gserviceaccount.com}"

echo "Granting Cloud Run Job execute permission:"
echo "  job=$JOB"
echo "  member=$API_SERVICE_ACCOUNT"

gcloud run jobs add-iam-policy-binding "$JOB" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="serviceAccount:${API_SERVICE_ACCOUNT}" \
  --role="roles/run.invoker"

echo "IAM configuration complete."
