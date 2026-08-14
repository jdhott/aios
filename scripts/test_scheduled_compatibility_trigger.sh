#!/bin/bash
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
JOB="${1:-aios-compat-quarter-hour}"

echo "Forcing one Cloud Scheduler compatibility request: $JOB"

gcloud scheduler jobs run "$JOB" \
  --project "$PROJECT" \
  --location "$REGION"

echo
echo "Request submitted."
echo "Check processor executions with:"
echo "  gcloud run jobs executions list --job=aios-processor --project=$PROJECT --region=$REGION --limit=3"
